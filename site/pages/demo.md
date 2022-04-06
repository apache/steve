Title: Quickstart Guide

## pySTeVe

### Quickstart Guide

  * `svn co https://svn.apache.org/repos/asf/steve/trunk/pysteve/`
  * Edit `steve.cfg` to suit your needs (karma, DB backend etc)
    * IF you choose ElasticSearch as backend, install the python module (pip install elasticsearch)
    * OR IF you choose files as your backend, run setup.py in the CLI directory.
 * Edit `httpd.conf`, add it to your existing httpd configuration
 * Set up authorization using htpasswd for admins, monitors etc
 * Go to `http://steve.example.org/admin` and set up an election
 * Start voting!


### Building a Docker image

You can also build pySTeVe as a Docker image using the Dockerfile locate in the `docker` directory:

 * `svn co https://svn.apache.org/repos/asf/steve/trunk/pysteve/`
 * `docker build -t pysteve docker/`
 * `docker run -i -p 127.0.0.1:80:80 pysteve`
 * Navigate to `http://localhost/admin` to set up stuff, using the default credentials (admin/demo)
