# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.9.4-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install gcc (necessary to build uvicorn)
RUN apt-get update && apt-get install wget gcc -y

# Install shared pip requirements
COPY ./common/requirements.txt .
RUN python -m pip install -r requirements.txt

# Install pip requirements
COPY ./api/requirements.txt .
RUN python -m pip install -r requirements.txt

# clean up
RUN apt remove wget gcc -y

# Persist bash history
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    && echo $SNIPPET >> "/root/.bashrc"

WORKDIR /app
COPY ./api/ /app/

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "80"]
