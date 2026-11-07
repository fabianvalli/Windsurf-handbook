# Windsurfing Handbook IIS review

Use this separate review app to share the merged handbook with invited reviewers. The regular `dist` preview and the Joomla bodies have no commenting feature. The existing CSC website and its 10-Step Guide are independent of this app.

Build on a machine with Python 3.10+ and the .NET 10 SDK:

```powershell
python tools/build_review.py
```

The command builds the handbook, publishes the review server, and prints an IIS folder and ZIP under `tmp/`. Use `--output` to choose a new output folder. Both outputs contain the same app; you can unzip and deploy without installing the SDK on IIS.

For a 64-bit Windows server that already has IIS's ASP.NET Core Module V2 but lacks the .NET 10 runtime, add `--self-contained-win-x64`. This package includes the runtime and runs the review server as its own process. Use `ReviewServer.exe` instead of `dotnet ReviewServer.dll` for a local test. Rebuild and redeploy the self-contained package to pick up .NET runtime updates.

For a local test, change to the printed IIS folder and run:

```powershell
dotnet ReviewServer.dll --urls http://127.0.0.1:8778
```

Open `http://127.0.0.1:8778/`. Stop with Ctrl+C. Local comments default to `App_Data` inside the test app, outside `wwwroot`. For fresh test data, set `Review__DataDirectory` to a separate local directory before starting. To run the isolated posting, image, and restart checks, run `python tools/check_review.py <published-folder>` from the repository.

## IIS setup

1. Install the [.NET 10 Hosting Bundle for IIS](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/iis/?view=aspnetcore-10.0#install-the-net-hosting-bundle) on the server. Copy the extracted package, including `web.config` and `wwwroot`, to a dedicated staging folder.
2. In IIS Manager create a separate HTTPS site or an **Application** such as `/windsurf-review` on the existing staging site. Use a dedicated app pool set to **No Managed Code** and point the application to the package root, where `web.config` sits. Use a single worker process. A static virtual directory alone will not run the comment server.
3. Set the app's `Review__DataDirectory` environment variable to a dedicated absolute directory outside the deploy folder and all IIS web roots, such as `D:\ReviewData\WindsurfHandbook`. Give the app pool identity read access to the app and Modify permission on the data directory. Keep and back up that directory when replacing the app. Follow [Microsoft's IIS environment-variable instructions](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/iis/advanced?view=aspnetcore-10.0#set-environment-variables) for the app or its pool.
4. Put the **entire app** behind the staging site's reviewer access controls, including `api/` and image URLs. The displayed name is self-entered and remembered in that browser; it does not verify identity or control access. All authorized reviewers can see posted comments and images. No external service receives them from this app.
5. Open the staging URL with a trailing slash. Check the chapter links and the equipment checkout photos, then submit a test comment and image. From a second browser, check that the marker and attachment are visible and add a reply. Reviewers' browsers need internet access for the shared CSC styles, banner, and existing lessons.

## Reviewing a page

Open **Review comments** to see the page's threads, or use the comment control in a section to link a new thread there. The numbered markers and thread links let you move between the comments and their section. Choose or paste up to three PNG, JPEG, GIF, or WebP images (5 MiB each) per post. Use **Reply** to keep the conversation in the same thread. The browser remembers your display name; use **Change name** on a shared device.

Keep `chapters.json` with the published app. Comment links are tied to the stable section IDs in that file. Preserve them when editing the handbook so reviewers can find existing comments after an update. Keep the review data out of Git, deployment ZIPs, and the Joomla import.
