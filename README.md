# Teledash Backend
 *Research and analysis software for Telegram*

## Repositories

* [Description](https://github.com/democ-de/teledash)
* [Frontend](https://github.com/democ-de/teledash-frontend)

## Configuration
See .env.example for default configuration.
- ``COMPOSE_PROJECT_NAME`` Project name.
- ``MONGO_HOST`` Hostname for MongoDB. Default: _"mongo"_ (forwards to the "mongo" docker container).
- ``MONGO_USER`` Username for MongoDB.
- ``MONGO_PASSWORD`` Password for MongoDB.
- ``MONGO_DB_NAME`` Name of MongoDB database.
- ``FLOWER_HOST`` Hostname for [Flower](https://flower.readthedocs.io/) (for debugging). Default: _"flower"_ (forwards to the "flower" docker container)
- ``FLOWER_PORT`` Port for Flower. Default: _"5555"_
- ``SCRAPE_CHATS_MAX_DAYS`` Number of days content in chats will be scraped backwards (when scraping for the first time). Set to *0* to scrape all content. Warning: Scraping all content of a chat can take several days. Default: _"7"_
- ``SCRAPE_CHATS_INTERVAL_MINUTES`` Interval in minutes new messages of chats will be scraped. Default: _"30"_
- ``SAVE_ATTACHMENT_TYPES`` Attachments that will be downloaded and stored. Default: _["photo","audio","document","animation","video","voice","video_note","sticker"]_
- ``KEEP_ATTACHMENT_FILES_DAYS`` Number of days attachments will be deleted after automatically. Set to *0* to keep files.
- ``STORAGE_ENDPOINT`` Endpoint for S3-compatible object storage e.g. MinIO. Default: _"host.docker.internal:9000"_ (forwards to the minio docker container)
- ``STORAGE_ACCESS_KEY`` API username for object storage.
- ``STORAGE_SECRET_KEY`` API key for object storage.
- ``JWT_SECRET`` JWT secret (token)
- ``JWT_LIFETIME_SECONDS`` Lifetime of JWT in seconds. Default: _"3600"_ (1 hour)
- ``OCR_ASR_FALLBACK_LANGUAGE`` Fallback [language code (ISO 639-1)](https://en.wikipedia.org/wiki/List_of_ISO_639-2_codes) for text and speech recognition if language of chat can't be detected automatically. Default: _"en"_
- ``OCR_ENABLED`` Whether text recognition (OCR) for images using [tesseract](https://tesseract-ocr.github.io/) is enabled. If enabled make sure _SAVE_ATTACHMENT_TYPES_ includes _"photo"_. Pretrained models are [available for 120+ languages](https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html) and will be downloaded automatically if _OCR_MODEL_TYPE_ is _"fast"_ or _"best"_. Default: _"fast"_
- ``OCR_MODEL_TYPE`` The model type being used for OCR. Can be _"fast"_, _"best"_ or _"custom"_. Fast models are fast and need less ressoures but are less accurate. Best models need more ressources, take longer but are more accurate.
- ``ASR_ENABLED`` Whether speech recognition (ASR) using [vosk](https://alphacephei.com/vosk/) is enabled. If enabled make sure _SAVE_ATTACHMENT_TYPES_ includes _"voice"_.
- ``ASR_LANGUAGE`` [Language code (ISO 639-1)](https://en.wikipedia.org/wiki/List_of_ISO_639-2_codes) for the language speech recognition (ASR) should be performed. Currently only one language is supported at once. Default: _"en"_
- ``ASR_MODEL_NAME`` Model name for speech recognition. Pretrained models are [available for 20+ languages](https://alphacephei.com/vosk/models) and will be downloaded automatically. For these languages usually exist _"small"_ and _"big"_ models. Small models are fast and need less ressoures but are less accurate. Big models need more ressources, take longer but are more accurate. Note: Big models require up to 16 GB memory. Default: _"vosk-model-small-en-us-0.15"_ (small english model)
- ``API_ALLOW_ORIGINS`` From which domain the API will be accessible. Default: _"["http://localhost:3000"]"_ (only accessible from localhost)

*Note: Scraping for the first time can take several hours to days to download and process all content depending on the configuration settings, available ressources and number of telegram clients used.*

---

## Export
### Database

The database can be exported in different ways:

#### Bash Script
There's a bash script that takes a collection name and exports that collection to a specified location ("outfile path") as a JSON-file.
Usage:
```shell
$ ./scripts/export/export.sh <collection name> <outfile path>
```

#### MongoDB Compass
Alternatively, you can export the database via the GUI [MongoDB Compass](https://docs.mongodb.com/compass/current/import-export/) as JSON or CSV.

### MinIO / Object Storage
Use the command-line [MinIO client](https://docs.min.io/docs/minio-client-complete-guide.html) (e. g. `mc cp  --recursive minio/[SOURCE] [TARGET]`), the web interface [MinIO console](https://docs.min.io/minio/baremetal/console/minio-console.html) (by default available at `http://localhost:9001`) or [Cyberduck](https://cyberduck.io/) (using a [generic S3 profile](https://docs.cyberduck.io/protocols/s3/)) if you want to download all attachments from the object storage.

---

## Development

We use [VS Code Remote-Containers](https://code.visualstudio.com/docs/remote/containers) for the development setup. To start developing in a Docker container, run the **Remote-Containers: Open Folder in Container**-Command from the Command Palette and select the *worker* or *api*-folder.

### API
#### Starting the API
```shell
$ uvicorn api.main:app --reload
```


### Worker
Start Celery by running the VSCode task "Celery workers".

To test the scraping tasks, execute in a python shell:

```python
>>> from worker.tasks import init_scrapers
>>> init_scrapers.delay()
```

### MinIO object storage
We use MinIO for object storage in development.

To setup a local MinIO instance, run:
```shell
$ mkdir -p ~/minio/data

$ docker run \
    -p 9000:9000 \
    -p 9001:9001 \
    --name minio1 \
    -v ~/minio/data:/data \
    -e "MINIO_ROOT_USER=username" \
    -e "MINIO_ROOT_PASSWORD=password" \
    quay.io/minio/minio server /data --console-address ":9001"
```
For more info check out the [MinIO Quickstart Guide](https://docs.min.io/docs/minio-docker-quickstart-guide.html).

### MinIO Client
If you want to access MinIO via CLI follow the [MinIO Client Guide](https://docs.min.io/docs/minio-client-complete-guide).

Then:
```shell
$ mc alias set <ALIAS> <YOUR-S3-ENDPOINT> [YOUR-ACCESS-KEY] [YOUR-SECRET-KEY] [--api API-SIGNATURE]
```
Alias is simply a short name to your cloud storage service.

#### Removing buckets
```shell
$ mc rb minio/[BUCKET_NAME] minio/[BUCKET_NAME] ... --force
```

### Useful Docker commands

#### Open authenticated MongoDB-shell in mongo container:
```shell
$ scripts/open-mongosh.sh
```

#### Recreate MongoDB indexes
The file `scripts/mongo-init.js` is executed once when Mongodb starts for the first time. To recreate all indexes (e.g. after dropping a collection), run:
```shell
$ scripts/rerun-mongo-init.sh
```


#### Open a shell inside container:
```shell
$ docker exec -it <container id or name> /bin/bash
```
As root:
```shell
$ docker exec -it --user root <container id or name> /bin/bash
```

---


### ToDos
- [ ] Add documentation for setup and deployment instructions
- [ ] Add documentation for [frontend](https://github.com/democ-de/teledash-frontend)
- [ ] Improve full text search (implement fuzzy search)
- [ ] Create JWT refresh endpoint for API
- [ ] Implement Role Based Access Control (RBAC)
- [ ] Handle failed downloads and clean up tmp directory
- [ ] Extract and store meta data for media files
- [ ] Extract and store text from documents
- [ ] Write tests

---

## Citation
Please cite Teledash in your publications if you used it for your research:
```BibTeX
@misc{teledash_2022,
  title={Teledash – analysis and research software for Telegram},
  url={https://github.com/democ-de/teledash},
  author={Weichbrodt, Gregor and Stanjek, Grischa},
  year={2022}
}
 ```