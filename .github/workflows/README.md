# GitHub Actions Workflow

## Simple Auto-Build on Main Branch

This workflow automatically builds and publishes a multi-platform Docker image when you push to the `main` branch.

### What It Does

- ✅ Triggers on push to `main` branch
- ✅ Builds for `linux/amd64` and `linux/arm64`
- ✅ Pushes to Docker Hub with `latest` tag
- ✅ Uses GitHub Actions cache for faster builds
- ✅ Can be triggered manually via GitHub UI

### Setup

1. **Add GitHub Secrets:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `DOCKER_USERNAME` - Your Docker Hub username (e.g., `ashraaf97`)
     - `DOCKER_PASSWORD` - Your Docker Hub access token

2. **Create Docker Hub Access Token:**
   - Go to https://hub.docker.com/settings/security
   - Click "New Access Token"
   - Name: `github-actions`
   - Permissions: Read, Write, Delete
   - Copy the token and add it as `DOCKER_PASSWORD` secret

### Usage

**Automatic (on push to main):**
```bash
git add .
git commit -m "Add new feature"
git push origin main
```

GitHub Actions will automatically:
1. Build multi-platform image
2. Push to `ashraaf97/gallery-dl-server-neo:latest`

**Manual trigger:**
1. Go to Actions tab
2. Click "Build and Push Docker Image"
3. Click "Run workflow"
4. Select branch (main)
5. Click "Run workflow"

### Image Location

After the workflow completes, your image will be at:
```bash
docker pull ashraaf97/gallery-dl-server-neo:latest
```

### Monitoring

- Go to the **Actions** tab to see build progress
- Click on a workflow run to see detailed logs
- Build typically takes 5-10 minutes

### Troubleshooting

**Build fails with authentication error:**
- Verify `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets are set correctly
- Make sure the Docker Hub token has write permissions

**Build is slow:**
- First build takes longer (~10 minutes)
- Subsequent builds use cache (~3-5 minutes)

**Want to skip a build:**
- Add `[skip ci]` to your commit message:
  ```bash
  git commit -m "Update docs [skip ci]"
  ```

### Workflow File

Location: `.github/workflows/docker-image.yaml`

Simple configuration:
- Builds on push to `main`
- Multi-platform support (amd64 + arm64)
- Pushes to Docker Hub
- Uses GitHub Actions cache

That's it! Simple and effective. 🚀
