FROM caddy:2-alpine@sha256:003a97808e781aa9f7e75cc2f43d34d461099031faf5e20faefb9f61126836f0
RUN chown -R 10001:10001 /data /config
COPY Caddyfile Caddyfile.production site.caddy /etc/caddy/
COPY public /srv
USER 10001:10001
EXPOSE 8080
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
