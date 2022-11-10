# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.9.4-slim
# TODO: consider upgrading to current stable e.g. 3.9.10-slim-bullseye

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# "procps" for pkill
# "protobuf-compiler", "g++" for cld3 build
# "wget" to download gpg key for custom repo
# "gnupg" for installing gpg key for custom repo
# "git" for vosk (on m1)
# "ffmpeg" for transcoding audio files before speech recognition
RUN apt-get update && apt-get install -y procps g++ protobuf-compiler gnupg wget git ffmpeg

# Add tesseract version 5 repo for debian binaries
RUN echo "deb https://notesalexp.org/tesseract-ocr5/$(. /etc/os-release && echo $VERSION_CODENAME)/ $(. /etc/os-release && echo $VERSION_CODENAME) main" \ 
    | tee /etc/apt/sources.list.d/notesalexp.list > /dev/null
# Install GPG key of repo
RUN wget -O - https://notesalexp.org/debian/alexp_key.asc | apt-key add -
# Install latest tesseract (version 5.X)
RUN apt-get update && apt-get install -y tesseract-ocr

# Install shared pip requirements
COPY ./common/requirements.txt .
RUN python -m pip install -r requirements.txt

# Install pip requirements
COPY ./worker/requirements.txt .
RUN python -m pip install -r requirements.txt

# clean up
# remove "protobuf-compiler", "g++" for cld3 build
RUN apt remove g++ protobuf-compiler wget -y
# remove git later

WORKDIR /app
COPY ./worker/ /app/

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app

# Persist bash history
ARG USERNAME=appuser

RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    && mkdir /commandhistory \
    && touch /commandhistory/.bash_history \
    && chown -R $USERNAME /commandhistory \
    && echo $SNIPPET >> "/home/$USERNAME/.bashrc"

# Create tmp directory
RUN mkdir /app/tmp \
    && chown -R $USERNAME /app/tmp

# Switch to non-root user
USER appuser
