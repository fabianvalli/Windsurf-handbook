using System.Diagnostics;
using System.Globalization;
using System.Text.Json;

sealed record Comment(int Id, string Page, string Section, int? ParentId, string Author, string Text,
    DateTimeOffset CreatedAt, CommentImage[] Images);
sealed record CommentImage(string Id, string Name);
sealed record Upload(string Name, string MediaType, byte[] Bytes);
sealed record StoredComment(Comment Comment, string[] MediaTypes, long ImageBytes);

sealed class ReviewException(int status, string message) : Exception(message)
{
    public int Status { get; } = status;
}

// Single-server store. Readers see only complete comment directories. A filesystem lock serializes
// writers even if two IIS worker processes briefly overlap during a recycle.
sealed class ReviewStore
{
    private const int MaxComments = 1000;
    private const long MaxImageBytes = 256 * 1024 * 1024;
    private readonly string directory;
    private readonly string lockPath;
    private readonly JsonSerializerOptions json;

    public ReviewStore(string root, JsonSerializerOptions json)
    {
        this.json = json;
        directory = Path.Combine(root, "comments");
        lockPath = Path.Combine(root, "write.lock");
        Directory.CreateDirectory(directory);
    }

    public Comment[] ReadComments(string page) => Entries()
        .OrderBy(entry => entry.Id)
        .Select(entry => ReadStored(entry.Path).Comment)
        .Where(comment => comment.Page == page).ToArray();

    public (string Path, string MediaType)? FindImage(string id)
    {
        // Only the normalized storage ID can reach the filesystem, never the upload's name.
        if (id.Length != 43 || id[10] != '-' || !TryParseCommentId(id[..10], out var commentId)
            || !Guid.TryParseExact(id.AsSpan(11), "N", out var imageKey) || id[11..] != imageKey.ToString("N"))
            return null;
        var path = CommentPath(commentId);
        if (!Directory.Exists(path))
            return null;
        var record = ReadStored(path);
        var index = Array.FindIndex(record.Comment.Images, image => image.Id == id);
        if (index < 0)
            return null;
        var filePath = Path.Combine(path, id + ".img");
        return File.Exists(filePath) ? (filePath, record.MediaTypes[index]) : null;
    }

    public async Task<Comment> Add(string page, string section, int? parentId, string author, string text,
        IReadOnlyList<Upload> images, CancellationToken cancellationToken)
    {
        await using var writeLock = await AcquireWriteLock(cancellationToken);
        // Uncommitted files left by a terminated process are safe to remove while holding the lock.
        foreach (var temp in Directory.EnumerateDirectories(directory, ".pending-*"))
            if (Guid.TryParseExact(Path.GetFileName(temp).AsSpan(9), "N", out _))
                RemovePending(temp);

        if (parentId is int parent)
        {
            var parentPath = CommentPath(parent);
            var parentComment = Directory.Exists(parentPath) ? ReadStored(parentPath).Comment : null;
            if (parentComment is null || parentComment.ParentId is not null || parentComment.Page != page
                || parentComment.Section != section)
                throw new ReviewException(400, "Replies must belong to a top-level comment in this section.");
        }

        var entries = Entries().ToArray();
        var newBytes = images.Sum(image => (long)image.Bytes.Length);
        if (entries.Length >= MaxComments || (newBytes > 0
            && entries.Sum(entry => ReadStored(entry.Path).ImageBytes) + newBytes > MaxImageBytes))
            throw new ReviewException(507, "The review storage limit has been reached.");

        var id = entries.Length == 0 ? 1 : checked(entries.Max(entry => entry.Id) + 1);
        var imageRefs = images.Select(image => new CommentImage($"{FormatId(id)}-{Guid.NewGuid():N}", image.Name)).ToArray();
        var comment = new Comment(id, page, section, parentId, author, text, DateTimeOffset.UtcNow, imageRefs);
        var data = new StoredComment(comment, images.Select(image => image.MediaType).ToArray(), newBytes);

        var pending = Path.Combine(directory, ".pending-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(pending);
        try
        {
            for (var i = 0; i < images.Count; i++)
                await WriteDurably(Path.Combine(pending, imageRefs[i].Id + ".img"), images[i].Bytes, cancellationToken);
            await WriteDurably(Path.Combine(pending, "record.json"), JsonSerializer.SerializeToUtf8Bytes(data, json), cancellationToken);
            cancellationToken.ThrowIfCancellationRequested();
            Directory.Move(pending, CommentPath(id));
        }
        finally
        {
            if (Directory.Exists(pending))
                RemovePending(pending);
        }
        return comment;
    }

    private IEnumerable<(int Id, string Path)> Entries()
    {
        foreach (var path in Directory.EnumerateDirectories(directory))
            if (TryParseCommentId(Path.GetFileName(path), out var id))
                yield return (id, path);
    }

    private string CommentPath(int id) => Path.Combine(directory, FormatId(id));
    private static string FormatId(int id) => id.ToString("D10", CultureInfo.InvariantCulture);
    private static bool TryParseCommentId(string value, out int id) =>
        int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out id)
        && id > 0 && value == FormatId(id);

    private StoredComment ReadStored(string path) =>
        JsonSerializer.Deserialize<StoredComment>(File.ReadAllBytes(Path.Combine(path, "record.json")), json)
        ?? throw new IOException("A review record is empty.");

    private static async Task WriteDurably(string path, byte[] bytes, CancellationToken cancellationToken)
    {
        await using var file = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None,
            bufferSize: 8192, FileOptions.Asynchronous);
        await file.WriteAsync(bytes, cancellationToken);
        file.Flush(flushToDisk: true);
    }

    private async Task<FileStream> AcquireWriteLock(CancellationToken cancellationToken)
    {
        var timer = Stopwatch.StartNew();
        while (true)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try { return new FileStream(lockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
            catch (IOException) when (timer.Elapsed < TimeSpan.FromSeconds(8))
            { await Task.Delay(50, cancellationToken); }
        }
    }

    private static void RemovePending(string path)
    {
        // The store creates only direct files in pending directories; never follow nested directories.
        if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
            throw new IOException("A pending review directory is not a regular directory.");
        foreach (var file in Directory.EnumerateFiles(path))
            File.Delete(file);
        Directory.Delete(path);
    }
}
