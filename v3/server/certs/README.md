# Certificate Creation and Usage

## Usage

In the `config.yaml` file under the `server` category are two values
that point to your server's certificate:

```yaml
server:
    certfile: server.crt
    keyfile: server.key
```

These files are relative to the `certs` sub-directory where the
`main.py` server script, or the files may be
absolute paths.

## Certificate Creation

If you do not have a server certificate to use, or you need a testing
and development certificate, then follow the instructions below.

**NOTE**: this documentation is based on the **mkcert** tool. Any standard toolchain
may be used to create the certificate and private key.

On Ubuntu:
```sh
$ sudo apt install mkcert
```

First step is to create a new Certificate Authority (CA) store on your local
machine.

**WARNING:** mkcert uses **sudo** to elevate privileges to modify
the local CA store on your machine. This was a surprise, when it modified
`/etc/ssl/certs` on my machine without a password prompt (Crostini with
a NOPASSWD config on my username).

Creating the CA is straightforward. You may/not receive a similar warning about "certutil".

```sh
$ mkcert -install
Created a new local CA 💥
The local CA is now installed in the system trust store! ⚡️
Warning: "certutil" is not available, so the CA can't be automatically installed in Firefox and/or Chrome/Chromium! ⚠️
Install "certutil" with "apt install libnss3-tools" and re-run "mkcert -install" 👈
```

This has created a CA certificate in your "trusted store" which may need
to be copied elsewhere. (eg. Certificate Manager in my Chrome browser on
my Chromebook)  The certificate appears to have a pattern like
`mkcert_development_CA_*.crt`.

Next is the creation of the server's certificate:

```sh
$ cd server/certs
$ mkcert localhost.apache.org localhost 127.0.0.1 ::1
Note: the local CA is not installed in the Firefox and/or Chrome/Chromium trust store.
Run "mkcert -install" for certificates to be trusted automatically ⚠️

Created a new certificate valid for the following names 📜
 - "localhost.apache.org"
 - "localhost"
 - "127.0.0.1"
 - "::1"

The certificate is at "./localhost.apache.org+3.pem" and the key at "./localhost.apache.org+3-key.pem" ✅

It will expire on 29 December 2027 🗓
```

_Note: on a different run, that "Note" about the local CA did not appear. YMMV_

Adjust the `config.yaml` to refer to these new files. The default `config.yaml.example`
config assumes the generated files are moved under the `server/certs` directory.

## Browser Trust

TBD: _more solutions besides Chrome_

### Chrome Browser

This is a self-signed certificate which is usually rejected by the Chrome browser.
To correct this, select the "Settings" menu option, then "Privacy and security",
then the "Security" option.
Within that pane, select "Manage certificates" which will open a new tab.
Select the "Installed by you" option.
Now select the "Import" button for "Trusted Certificates" and choose the `.pem`
that was just generated. Should be `localhost.apache.org+3.pem` (not the keyfile!).

This should now provide trust to `localhost` for your dev/test operation.
