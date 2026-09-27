FROM hashicorp/terraform:1.16.4

USER root

COPY romashlashes-rootCA.crt /usr/local/share/ca-certificates/romashlashes-rootCA.crt

RUN if command -v update-ca-certificates >/dev/null 2>&1; then       update-ca-certificates;     else       cat /usr/local/share/ca-certificates/romashlashes-rootCA.crt >> /etc/ssl/certs/ca-certificates.crt;     fi

COPY terraform.tfrc /etc/terraformrc

ENV TF_CLI_CONFIG_FILE=/etc/terraformrc

ENTRYPOINT []
