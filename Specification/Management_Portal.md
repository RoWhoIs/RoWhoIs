# RoWhoIs Management Portal

> [!CAUTION]
> The management portal requires no authentication to access, as it's assumed this will be hosted on a private network.
> Please ensure you are hosting an instance on a secure network.


## Introduction

The RoWhoIs management portal is an internal tool for the server administrator to easily update, restart, start, shutdown, and modify RoWhoIs to meet their user's needs. This is also called the RMP.

## Objective

The objective of the RoWhoIs management portal is to provide an easy-to-use and efficient management utility for administrators to manage RoWhoIs without having to enter the active terminal space or remotely tunnel into their server.

## Requirements

[Spec Designer to include]

## Design

[Spec Designer to include]

## Usage

The management portal is a web interface hosted locally to port 63415.
From any standard web browser, like Firefox or Chrome, and on the same network as your server, enter the designated IP for the computer, followed by the port.
An example of this is `http://192.168.1.103:63415`.

[Needs to include more information]

## Error Handling

Any errors encountered in the management portal are logged to the primary log file locally on your server.

[Needs to include more information]

## Testing

[Spec Designer include test steps]

## Security

The management portal assumes that only administrators will be accessing the local area network, and as such, no credentials are required to access the portal.