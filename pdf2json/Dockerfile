FROM alpine:3.19 AS certbuilder
RUN apk add openssl
WORKDIR /certs
RUN openssl req -nodes -new -x509 -subj="/C=US/ST=Denial/L=springfield/O=Dis/CN=localhost" -keyout server.key -out server.cert

FROM node:lts-alpine3.19
COPY --from=certbuilder /certs/ /certs
COPY ./package.* /server/
RUN cd /server && npm install --production
COPY ./*.js /server/
ENTRYPOINT ["/server/server.js"]
