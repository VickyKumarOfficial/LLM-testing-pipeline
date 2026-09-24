# Deploy the benchmark API to Vercel

This deployment serves saved run artifacts. It does not run Ollama. The laptop
can be offline once approved runs are published to private Blob storage.

## Deployment entry point

Vercel detects the FastAPI application exported by root `index.py`. The
`.vercelignore` file excludes benchmark data, scores, prompts, profiles,
fine-tuning material, and local databases from the deployment bundle. It keeps
`niera_api/static/index.html` because the API serves that review page.

## Set up the Vercel project

1. Create a Vercel project from this Git repository, with the repository root
   as its Root Directory.
2. Add a PostgreSQL integration and a **private** Vercel Blob store.
3. Set these Production and Preview environment variables in Vercel:

   - `NIERA_API_STORAGE_BACKEND=remote`
   - `NIERA_API_TOKEN`: a long random owner credential
   - `DATABASE_URL`: the PostgreSQL connection string
   - `BLOB_READ_WRITE_TOKEN`: the private Blob store token, if the project is
     not using Vercel's automatically provisioned Blob identity

   Leave `NIERA_API_EXPOSE_SYSTEM_PROMPT` and `NIERA_API_EXPOSE_PROFILE`
   unset or false. Do not put credentials in this repository.

4. Deploy a Preview first. Check `/`, `/api/v1/health`, owner authentication,
   share-link access, comparison, and exports. Confirm that source data and
   score files are absent from the deployment.
5. Deploy to Production after the Preview checks and content review pass.

Vercel recognizes `index.py` as a FastAPI entry point and installs Python
dependencies from `requirements.txt`. The Python runtime currently supports
FastAPI deployments. See [Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi)
and [deployment ignore rules](https://vercel.com/docs/deployments/vercel-ignore).

## Publish approved runs

From a trusted local machine, configure `DATABASE_URL` and
`BLOB_READ_WRITE_TOKEN`, then use the checked publisher documented in
`README.md`. Run the `--dry-run` first and inspect the artifact list. Upload only
approved run IDs. Prompt/profile snapshots require explicit publisher flags.

Remote API reads use only catalog entries marked `published`. They verify the
archive digest before returning content. Share credentials and run metadata
live in PostgreSQL; the result archive lives in private Blob storage.

## Current setup limit

The repository is prepared for deployment, but no Vercel CLI is installed, no
Vercel project is linked in `.vercel/`, and no database or Blob credentials are
configured in this workspace. A live deployment therefore still needs an
authenticated Vercel project and its storage integrations.
