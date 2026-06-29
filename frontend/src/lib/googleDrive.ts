/**
 * Google Drive integration using Google Identity Services (GIS).
 *
 * SETUP (one-time, ~5 minutes):
 * ─────────────────────────────
 * 1. Go to https://console.cloud.google.com/
 * 2. Create a project (or select an existing one)
 * 3. Enable the Google Drive API:
 *    APIs & Services → Enable APIs → search "Google Drive API" → Enable
 * 4. Create OAuth credentials:
 *    APIs & Services → Credentials → Create Credentials → OAuth client ID
 *    • Application type: Web application
 *    • Name: AI Career Coach
 *    • Authorized JavaScript origins: http://localhost:3000
 *    • Click Create — copy the Client ID
 * 5. Add to frontend/.env.local:
 *    NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
 *    NEXT_PUBLIC_GDRIVE_FOLDER_NAME=AI Career Coach Resumes
 * 6. Restart the dev server.
 */

const DRIVE_UPLOAD_URL =
  "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink";
const DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files";

const DOCX_MIME =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

// ---------------------------------------------------------------------------
// Token acquisition (GIS pop-up)
// ---------------------------------------------------------------------------

function getGoogleClientId(): string {
  const id = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  if (!id) {
    throw new Error(
      "NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set.\n" +
        "Add it to frontend/.env.local and restart the dev server.\n" +
        "See src/lib/googleDrive.ts for full setup instructions."
    );
  }
  return id;
}

function requestAccessToken(): Promise<string> {
  return new Promise((resolve, reject) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const google = (window as any).google;
    if (!google?.accounts?.oauth2) {
      reject(
        new Error(
          "Google Identity Services not loaded. " +
            "Make sure the GIS script is in layout.tsx."
        )
      );
      return;
    }

    const client = google.accounts.oauth2.initTokenClient({
      client_id: getGoogleClientId(),
      scope: "https://www.googleapis.com/auth/drive.file",
      callback: (response: { access_token?: string; error?: string }) => {
        if (response.error || !response.access_token) {
          reject(new Error(response.error || "Failed to get access token"));
        } else {
          resolve(response.access_token);
        }
      },
    });

    client.requestAccessToken({ prompt: "consent" });
  });
}

// ---------------------------------------------------------------------------
// Folder helpers
// ---------------------------------------------------------------------------

async function getOrCreateFolder(
  folderName: string,
  token: string
): Promise<string> {
  // Try to find the folder first
  const search = await fetch(
    `${DRIVE_FILES_URL}?q=name='${encodeURIComponent(folderName)}' and mimeType='application/vnd.google-apps.folder' and trashed=false&fields=files(id,name)`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const searchData = await search.json();
  if (searchData.files?.length > 0) {
    return searchData.files[0].id as string;
  }

  // Create it
  const create = await fetch(DRIVE_FILES_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: folderName,
      mimeType: "application/vnd.google-apps.folder",
    }),
  });
  const folder = await create.json();
  return folder.id as string;
}

// ---------------------------------------------------------------------------
// Main upload function
// ---------------------------------------------------------------------------

export interface DriveUploadResult {
  id: string;
  name: string;
  webViewLink: string;
}

export async function uploadDocxToDrive(
  blob: Blob,
  filename: string
): Promise<DriveUploadResult> {
  const folderName =
    process.env.NEXT_PUBLIC_GDRIVE_FOLDER_NAME || "AI Career Coach Resumes";

  // 1. Get OAuth token (opens a Google sign-in popup)
  const token = await requestAccessToken();

  // 2. Find or create the target folder
  const folderId = await getOrCreateFolder(folderName, token);

  // 3. Upload the file using multipart upload
  const metadata = {
    name: filename,
    mimeType: DOCX_MIME,
    parents: [folderId],
  };

  const form = new FormData();
  form.append(
    "metadata",
    new Blob([JSON.stringify(metadata)], { type: "application/json" })
  );
  form.append("file", blob, filename);

  const upload = await fetch(DRIVE_UPLOAD_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });

  if (!upload.ok) {
    const err = await upload.json();
    throw new Error(err.error?.message || "Upload to Google Drive failed");
  }

  return upload.json() as Promise<DriveUploadResult>;
}
