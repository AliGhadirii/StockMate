# Google Service Account Setup (Recommended for Automation)

## Why Service Accounts Are Better

✅ **No OAuth flow needed**  
✅ **Tokens never expire**  
✅ **Fully automated - set and forget**  
✅ **More secure for server applications**  
✅ **No "testing/production" mode issues**

## Setup Steps

### Step 1: Create a Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **IAM & Admin** → **Service Accounts**
4. Click **"+ CREATE SERVICE ACCOUNT"**
5. Fill in:
   - **Service account name**: `stockmate-drive-access`
   - **Description**: `ist h`
6. Click **"Create and Continue"**
7. Skip the optional steps (no roles needed)
8. Click **"Done"**

### Step 2: Create a Key

1. Click on the service account you just created
2. Go to the **"Keys"** tab
3. Click **"Add Key"** → **"Create new key"**
4. Select **"JSON"** format
5. Click **"Create"**
6. A JSON file will be downloaded - **keep this safe!**

The JSON file looks like this:
```json
{
  "type": "service_account",
  "project_id": "your-project-123456",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "stockmate-drive-access@your-project-123456.iam.gserviceaccount.com",
  "client_id": "123456789...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### Step 3: Enable Drive API

1. Go to **APIs & Services** → **"Enable APIs and Services"**
2. Search for **"Google Drive API"**
3. Click **"Enable"**

### Step 4: Share Your Drive File

1. Open your `investment_data.json` file in Google Drive
2. Click **"Share"**
3. Copy the **service account email** from the JSON file (looks like `stockmate-drive-access@your-project-123456.iam.gserviceaccount.com`)
4. Paste it into the share dialog
5. Give it **"Editor"** permissions
6. Click **"Send"** (uncheck "Notify people" if you want)

### Step 5: Configure Lambda Environment Variables

Instead of the OAuth variables, you'll use:

```
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
GOOGLE_DRIVE_FILE_ID=your_file_id_here
```

**Note**: The entire JSON file content goes in one environment variable.

Alternatively (more secure), upload the JSON file to AWS Secrets Manager and reference it from Lambda.

## Implementation

The updated code will automatically detect if you're using Service Account or OAuth:
- If `GOOGLE_SERVICE_ACCOUNT_JSON` is set → use Service Account (recommended)
- If `GOOGLE_CLIENT_ID` is set → use OAuth (fallback)

## Security Best Practices

1. **Never commit the service account JSON file to git** (already in .gitignore)
2. Store it in AWS Secrets Manager or AWS Systems Manager Parameter Store
3. The Lambda execution role should have permission to read the secret
4. Rotate the service account key periodically (every 90 days recommended)

## Comparison

| Feature | OAuth Refresh Token | Service Account |
|---------|-------------------|-----------------|
| Setup Complexity | Medium | Easy |
| Token Expiration | Can expire if app in testing | Never expires |
| Maintenance | Need to republish app | Zero maintenance |
| Security | User-based | Service-based |
| Best For | User-facing apps | Automation/servers |

