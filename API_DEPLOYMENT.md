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

Create a sanitized archive locally, then upload it from the deployed owner page.
The Vercel function uses its own database and Blob credentials, so they do not
need to be copied to the laptop. For example:

```sh
python scripts/publish_run.py 20260922_104435_c7a061 --dry-run
python scripts/publish_run.py 20260922_104435_c7a061 --write-archive .api-data/publish-ready/20260922_104435_c7a061.zip
```

Open `/`, choose **Owner**, enter `NIERA_API_TOKEN`, load runs, then select the
ZIP under **Publish benchmark runs**. The endpoint accepts archives up to 4 MB,
validates the run manifest and results, removes internal `metadata.thinking`
and local filesystem paths, and writes the sanitized archive to private Blob
storage and its catalog record to PostgreSQL. It rejects system prompt and
student profile files. `--dry-run` does not upload anything.

Remote API reads use only catalog entries marked `published`. They verify the
archive digest before returning content. Share credentials and run metadata
live in PostgreSQL; the result archive lives in private Blob storage.

## Current setup

The Vercel project, PostgreSQL integration, private Blob store, production
deployment, and local Vercel CLI link have been configured. Vercel keeps its
sensitive environment values unavailable to local `env pull` and `env run`
commands. The owner upload page avoids exporting those secrets to the laptop.
