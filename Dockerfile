FROM rstropek/pandoc-latex:3.1

RUN apk add --no-cache --update \
    make \
    python3 py-pip \
    fontconfig ttf-freefont font-noto

WORKDIR /app

RUN tlmgr update --self
RUN tlmgr install ragged2e xltxtra realscripts wallpaper eso-pic \
    titlesec arydshln spreadtab enumitem xstring

COPY ./requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

COPY ./data /app/data
COPY ./src /app/src
COPY ./makefile /app/makefile
COPY ./docker-entrypoint.sh /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]

EXPOSE 1111
