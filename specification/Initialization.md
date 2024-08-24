# RoWhoIs Initialization

## Introduction

This specification outlines the server initialization of RoWhoIs.

## Objective

Create a local [Management Portal](Management_Portal.md) server/client, and automatically start the discord client.

## Requirements

This requires the Discord bot token for the given instance type (Developer Mode/Production Mode). This can be set by specifying a start flag.

If the instance is running in Developer Mode, a `dev-bot` token will be required. Subsequently, if the instance is in Production mode, a `prod-bot` token will be required.

These can all be found in `config.json`, which is a required file. This file must follow the structure of `config.template.json`.

## Design

[Spec designer include design here]

## Usage

The `-OO` flag, or optimization level 2, enables a higher level of optimization in Python, which removes docstrings and asserts from the compiled bytecode. This can result in a smaller memory footprint and faster execution, which is required for production instances of RoWhoIs.

```bash
python -OO server.py -p
```

The `-p` flag denotes that we are running a production instance of RoWhois.

If you are running a development instance, it is permitted to run at optimization level 1.

```bash
python -O server.py -d
```

Note the `-d` flag to designate that we are running the server in development mode.

## Error Handling

[Spec designer include error handling here]

## Testing

[Spec designer include testing instructions here]