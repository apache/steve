# Getting Started

## Prerequisites

STeVe v3 uses `uv` as the project manager. You can install `uv` via:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For other installation methods, see the [uv installation documentation](https://docs.astral.sh/uv/getting-started/installation/).

You'll also need to have [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) and [SQLite 3.x](https://www.sqlite.org/download.html) installed on your system. You can verify their installation by running:

```shell
git --version
sqlite3 --version
```

## Cloning the Repository

Clone the STeVe repository from GitHub:

```shell
git clone https://github.com/apache/steve.git
```

## Setting Up the Development Environment

First of all, head over to the `v3/` directory. This is where all the current development is happening.

```shell
cd steve  # navigate to the cloned repository
cd v3     # navigate to the v3 directory
```

Run the following command to set up the development environment using `uv`:

```shell
uv sync
```

## Preparing the Database

Head into the `server` directory for preparing data:

```shell
cd server
```

Create the steve.db file by loading the schema:

```shell
sqlite3 steve.db < ../schema.sql
```

Load steve.db's "person" table with ASF userids. For this step, you will need access to the ASF LDAP server. If you don't have access, please reach out on the developer mailing list or Slack channel for assistance.

```shell
cat > bin/bind.txt
# <2 magic lines for user/pass; talk to me on Slack>
```

Once bind.txt is ready, run the LDAP loading script (this may take a few minutes):

```shell
uv run bin/asf-load-ldap.py
```

Then prepare some fake testing data:

```shell
uv run bin/load-fakedata.py --owner-pid <your_asf_id> # e.g., tison
```

All the data is now prepared.

## Running the Server

Ensure you are in the `server` directory.

Before running the server, you need to create the config file and generate server certificates.

To create the config file, copy the example config:

```shell
cp config.yaml.example config.yaml
```

Then, follow the instructions in [`server/certs/README.md`](../server/certs/README.md) to create self-signed certificates for development purposes.

Now, you can run the server with:

```shell
uv run main.py # ensure you are in the server/ directory
```

Point your browser to https://localhost:58383/

Congratulations! You should see the STeVe v3 web interface.

If you modify anything (code, templates), then the server should automatically reload the change.

If you run into a problem, please reach out on the developer mailing list or Slack channel for assistance.
