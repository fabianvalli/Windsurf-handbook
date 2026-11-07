using System.Globalization;
using System.Text.Json;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.StaticFiles;

const int maxUpload = 5 * 1024 * 1024;
const int maxImages = 3;
const int maxRequest = 16 * 1024 * 1024;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(options => options.Limits.MaxRequestBodySize = maxRequest);
builder.Services.Configure<IISServerOptions>(options => options.MaxRequestBodySize = maxRequest);
builder.Services.Configure<FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = maxUpload;
    options.MultipartBoundaryLengthLimit = 128;
    options.MultipartHeadersCountLimit = 8;
    options.MultipartHeadersLengthLimit = 8192;
    options.ValueCountLimit = 8;
    options.ValueLengthLimit = 16000;
});

var app = builder.Build();
var json = new JsonSerializerOptions(JsonSerializerDefaults.Web);
var contentRoot = Path.GetFullPath(app.Environment.ContentRootPath);
var webRoot = app.Environment.WebRootPath ?? Path.Combine(contentRoot, "wwwroot");
var chapters = JsonSerializer.Deserialize<Chapter[]>(File.ReadAllText(Path.Combine(contentRoot, "chapters.json")), json)
    ?? throw new InvalidDataException("Missing handbook chapters.");
var sections = chapters.ToDictionary(chapter => chapter.Slug,
    chapter => chapter.Topics.Append("page").ToHashSet(StringComparer.Ordinal), StringComparer.Ordinal);
if (!sections.Keys.ToHashSet(StringComparer.Ordinal).SetEquals(["index", "sailing-skills", "equipment-reference"]))
    throw new InvalidDataException("Unexpected handbook chapters.");

var configuredPath = builder.Configuration["Review:DataDirectory"];
var dataRoot = string.IsNullOrWhiteSpace(configuredPath)
    // ASP.NET serves only wwwroot; App_Data is also a hidden segment in a default IIS installation.
    ? Path.Combine(contentRoot, "App_Data")
    : Path.GetFullPath(configuredPath, contentRoot);
var relativeDataPath = Path.GetRelativePath(webRoot, dataRoot);
if (!Path.IsPathFullyQualified(relativeDataPath) && relativeDataPath != ".."
    && !relativeDataPath.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal))
    throw new InvalidOperationException("Review data must be stored outside the public wwwroot folder.");

var store = new ReviewStore(dataRoot, json);
using var uploads = new SemaphoreSlim(4);

app.Use(async (context, next) =>
{
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["X-Robots-Tag"] = "noindex, nofollow";
    if (context.Request.Path.StartsWithSegments("/api", StringComparison.OrdinalIgnoreCase))
        context.Response.Headers.CacheControl = "no-store";
    try { await next(); }
    catch (Exception exception) when (context.Request.Path.StartsWithSegments("/api", StringComparison.OrdinalIgnoreCase)
        && !context.Response.HasStarted && exception is IOException or UnauthorizedAccessException or JsonException)
    {
        app.Logger.LogError(exception, "Could not access the review store.");
        await Error(503, "The review store is temporarily unavailable. Try again later.").ExecuteAsync(context);
    }
});
var mimeTypes = new FileExtensionContentTypeProvider();
mimeTypes.Mappings[".webp"] = "image/webp";
app.UseDefaultFiles();
app.UseStaticFiles(new StaticFileOptions { ContentTypeProvider = mimeTypes });

app.MapGet("/api/comments", (HttpRequest request) =>
{
    var page = request.Query["page"];
    if (page.Count != 1 || !sections.ContainsKey(page[0] ?? ""))
        return Error(400, "Choose a valid handbook page.");
    return Results.Json(store.ReadComments(page[0]!), json);
});

app.MapGet("/api/images/{id}", (string id, HttpResponse response) =>
{
    var image = store.FindImage(id);
    if (image is null)
        return Error(404, "Image not found.");
    response.Headers.ContentSecurityPolicy = "default-src 'none'; sandbox";
    response.Headers["Cross-Origin-Resource-Policy"] = "same-origin";
    return Results.File(image.Value.Path, image.Value.MediaType);
});

app.MapPost("/api/comments", async (HttpRequest request, CancellationToken cancellationToken) =>
{
    // A browser cannot attach this header from another origin without CORS; this app enables no CORS.
    if (request.Headers["X-Handbook-Review"].Count != 1 || request.Headers["X-Handbook-Review"][0] != "1")
        return Error(403, "This submission must come from the handbook review form.");
    if (!request.HasFormContentType || !(request.ContentType ?? "").StartsWith("multipart/form-data", StringComparison.OrdinalIgnoreCase))
        return Error(415, "Send the comment using the handbook review form.");
    if (request.ContentLength is > maxRequest)
        return Error(413, "This upload is too large.");
    if (!uploads.Wait(0, cancellationToken))
        return Error(429, "The review form is busy. Try again in a moment.");

    try
    {
        IFormCollection form;
        try { form = await request.ReadFormAsync(cancellationToken); }
        catch (BadHttpRequestException exception) when (exception.StatusCode == 413)
        { return Error(413, "This upload is too large."); }
        catch (InvalidDataException)
        { return Error(400, "The form could not be read. Images may be at most 5 MiB each."); }
        catch (BadHttpRequestException)
        { return Error(400, "The form could not be read."); }

        if (form.Any(field => field.Value.Count != 1 || field.Key is not ("page" or "section" or "parentId" or "author" or "text"))
            || form.Files.Any(file => file.Name != "images"))
            return Error(400, "The form contains unexpected fields.");

        var page = form["page"].ToString();
        var section = form["section"].ToString();
        if (!sections.TryGetValue(page, out var allowed) || !allowed.Contains(section))
            return Error(400, "Choose a valid handbook page and section.");
        var author = form["author"].ToString().Trim();
        var text = form["text"].ToString().Trim();
        if (author.Length is < 1 or > 80 || author.Any(char.IsControl))
            return Error(400, "Enter a name of 1 to 80 characters.");
        if (text.Length > 4000 || text.Any(c => char.IsControl(c) && c is not ('\t' or '\r' or '\n')))
            return Error(400, "Enter up to 4,000 characters of plain text.");

        int? parentId = null;
        var rawParentId = form["parentId"].ToString();
        if (rawParentId.Length > 0)
        {
            if (!int.TryParse(rawParentId, NumberStyles.None, CultureInfo.InvariantCulture, out var parent) || parent <= 0)
                return Error(400, "Choose a valid comment to reply to.");
            parentId = parent;
        }

        if (form.Files.Count > maxImages)
            return Error(400, "Attach at most three images.");
        if (text.Length == 0 && form.Files.Count == 0)
            return Error(400, "Enter a comment or attach an image.");

        var images = new List<Upload>();
        foreach (var file in form.Files)
        {
            if (file.Length is <= 0 or > maxUpload)
                return Error(413, "Images must be nonempty and no larger than 5 MiB each.");
            var data = new byte[(int)file.Length];
            await using var stream = file.OpenReadStream();
            await stream.ReadExactlyAsync(data, cancellationToken);
            var mediaType = ImageFormats.Detect(data);
            if (mediaType is null)
                return Error(400, "Attach a valid PNG, JPEG, GIF, or WebP image.");
            var name = Path.GetFileName(file.FileName.Replace('\\', '/'));
            name = string.Concat(name.Where(c => !char.IsControl(c)).Take(120)).Trim();
            images.Add(new Upload(name.Length == 0 ? "Image" : name, mediaType, data));
        }

        var record = await store.Add(page, section, parentId, author, text, images, cancellationToken);
        return Results.Json(record, json, statusCode: 201);
    }
    catch (ReviewException exception) { return Error(exception.Status, exception.Message); }
    finally { uploads.Release(); }
});

app.Run();

static IResult Error(int status, string error) => Results.Json(new { error }, statusCode: status);

record Chapter(string Slug, string[] Topics);
