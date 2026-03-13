# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automatically building and publishing multi-platform Docker images.

## Available Workflows

### 1. `docker-build-push.yml` (Full-Featured)

**Features:**
- ✅ Multi-platform builds (linux/amd64, linux/arm64)
- ✅ Automatic tagging based on git tags and branches
- ✅ Semantic versioning support
- ✅ Manual workflow dispatch with custom version
- ✅ Docker layer caching for faster builds
- ✅ Automatic Docker Hub description updates
- ✅ Build on push to main/master branches
- ✅ Build on pull requests (without pushing)
- ✅ Build on git tags

**Triggers:**
- Push to `main` or `master` branch
- Git tags matching `v*.*.*` (e.g., v1.0.0)
- Pull requests
- Manual trigger via GitHub UI

### 2. `docker-build-push-simple.yml` (Minimal)

**Features:**
- ✅ Multi-platform builds (linux/amd64, linux/arm64)
- ✅ Push to Docker Hub with `latest` and SHA tags
- ✅ Simple configuration

**Triggers:**
- Push to `main` or `master` branch
- Manual trigger via GitHub UI

## Setup Instructions

### Step 1: Create Docker Hub Access Token

1. Go to [Docker Hub](https://hub.docker.com/)
2. Click on your profile → Account Settings
3. Go to **Security** → **New Access Token**
4. Name: `github-actions`
5. Permissions: **Read, Write, Delete**
6. Click **Generate**
7. **Copy the token** (you won't see it again!)

### Step 2: Add GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | e.g., `johndoe` |
| `DOCKERHUB_TOKEN` | The access token from Step 1 | The token you just created |

### Step 3: Enable GitHub Actions

1. Go to **Settings** → **Actions** → **General**
2. Under "Actions permissions", select:
   - ✅ **Allow all actions and reusable workflows**
3. Under "Workflow permissions", select:
   - ✅ **Read and write permissions**
4. Click **Save**

### Step 4: Choose Your Workflow

**Option A: Use the full-featured workflow (Recommended)**
- Keep `docker-build-push.yml`
- Delete or disable `docker-build-push-simple.yml`

**Option B: Use the simple workflow**
- Keep `docker-build-push-simple.yml`
- Delete or disable `docker-build-push.yml`

## Usage

### Automatic Builds

Once set up, builds will trigger automatically:

**On every push to main/master:**
```bash
git add .
git commit -m "Update code"
git push origin main
```

**On git tags (full workflow only):**
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Manual Builds

1. Go to **Actions** tab in your GitHub repository
2. Click on the workflow name
3. Click **Run workflow**
4. (For full workflow) Enter optional version tag
5. Click **Run workflow**

## Tagging Strategy

### Full Workflow (`docker-build-push.yml`)

Creates multiple tags automatically:

| Trigger | Tags Created | Example |
|---------|--------------|---------|
| Push to main | `latest`, `main-<sha>` | `latest`, `main-abc1234` |
| Git tag v1.2.3 | `v1.2.3`, `1.2`, `1`, `latest` | Semantic versioning |
| Pull request | `pr-123` | For testing (not pushed) |
| Manual with version | Custom version + `latest` | User-defined |

### Simple Workflow (`docker-build-push-simple.yml`)

Creates two tags:
- `latest` - Always points to the most recent build
- `<git-sha>` - Specific commit SHA

## Example: Release Workflow

### 1. Create a new release

```bash
# Make your changes
git add .
git commit -m "Add cookies file upload feature"

# Create a version tag
git tag v1.0.0

# Push changes and tag
git push origin main
git push origin v1.0.0
```

### 2. GitHub Actions will automatically:
- Build for linux/amd64 and linux/arm64
- Push to Docker Hub with tags:
  - `yourusername/gallery-dl-server-neo:latest`
  - `yourusername/gallery-dl-server-neo:v1.0.0`
  - `yourusername/gallery-dl-server-neo:1.0`
  - `yourusername/gallery-dl-server-neo:1`

### 3. Users can pull the image:

```bash
docker pull yourusername/gallery-dl-server-neo:latest
docker pull yourusername/gallery-dl-server-neo:v1.0.0
```

## Monitoring Builds

### View Build Status

1. Go to **Actions** tab
2. Click on a workflow run
3. View logs for each step

### Build Badge

Add this to your README.md:

```markdown
![Docker Build](https://github.com/YOUR_USERNAME/gallery-dl-server-neo/actions/workflows/docker-build-push.yml/badge.svg)
```

Replace `YOUR_USERNAME` with your GitHub username.

## Troubleshooting

### Issue: "Error: Cannot connect to the Docker daemon"

**Solution**: This is normal - GitHub Actions uses Docker Buildx which doesn't require the daemon.

### Issue: "denied: requested access to the resource is denied"

**Solution**: 
1. Verify `DOCKERHUB_USERNAME` secret is correct
2. Verify `DOCKERHUB_TOKEN` is valid and has write permissions
3. Make sure the repository exists on Docker Hub or set it to auto-create

### Issue: Build is slow

**Solution**: The first build will be slow. Subsequent builds use GitHub Actions cache and will be much faster.

### Issue: "no matching manifest for linux/amd64"

**Solution**: Make sure QEMU and Buildx are set up (they are in the workflows).

## Advanced Configuration

### Build only on specific paths

Add to the workflow:

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'gallery_dl_server/**'
      - 'Dockerfile'
      - 'requirements.txt'
```

### Add build notifications

Add a notification step:

```yaml
- name: Notify on success
  if: success()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Build for more platforms

Update the `PLATFORMS` env variable:

```yaml
env:
  PLATFORMS: linux/amd64,linux/arm64,linux/arm/v7,linux/ppc64le
```

## Cost Considerations

- ✅ GitHub Actions is **free** for public repositories
- ✅ Private repositories get 2,000 minutes/month free
- ✅ Multi-platform builds count as multiple jobs
- ✅ Use caching to reduce build time and costs

## Security Best Practices

1. ✅ Use Personal Access Tokens, not passwords
2. ✅ Store credentials as GitHub Secrets
3. ✅ Use minimal token permissions
4. ✅ Enable 2FA on Docker Hub
5. ✅ Regularly rotate tokens
6. ✅ Review workflow permissions

## Next Steps

1. ✅ Set up GitHub Secrets (DOCKERHUB_USERNAME, DOCKERHUB_TOKEN)
2. ✅ Push code to trigger first build
3. ✅ Verify image on Docker Hub
4. ✅ Add build badge to README
5. ✅ Set up branch protection rules
6. ✅ Configure notifications (optional)

## Support

For issues:
- Check the Actions tab for build logs
- Review GitHub Actions documentation
- Check Docker Hub for published images
- Verify secrets are configured correctly
