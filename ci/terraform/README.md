# terraform-ci image

Build context must contain:

- Dockerfile
- terraform.tfrc
- romashlashes-rootCA.crt

The CA certificate is public. Never place the CA private key in this directory.
