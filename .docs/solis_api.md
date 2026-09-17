# Obtaining SolisCloud API Credentials

The SolisCloud API provides programmatic access to data associated with a Solis inverter and its associated plant. API access must first be enabled for the SolisCloud account before API credentials can be generated.

> **Note:** API access is separate from remote-control access. Requesting API access does not by itself provide remote control of the inverter.

## Prerequisites

Before requesting API access, make sure that:

* The inverter is registered and visible in your **SolisCloud** account.
* You have access to the email address associated with the SolisCloud account.
* You know the SolisCloud account/plant associated with the inverter.
* You have access to a web browser. The API activation process is performed through the web version of SolisCloud.

If you do not already have a SolisCloud account, create one before requesting API access.

## 1. Request API Access

API access must first be enabled by Solis.

1. Create or log in to your account on the [Solis Service Center](https://solis-service.solisinverters.com/).
2. Submit a support ticket requesting **API Access**.
3. Select **API Access Request** as the ticket type.
4. Provide the email address associated with your SolisCloud account.

Solis will process the request and enable API access for the account. According to the official Solis documentation, API access is currently available to end users and is separate from remote-control permissions.

See the official Solis guide:

[Request API Access - SolisCloud](https://solis-service.solisinverters.com/en/support/solutions/articles/44002212561-request-api-access-soliscloud)

## 2. Activate API Access in SolisCloud

Once Solis has enabled API access, log in to the **SolisCloud web portal**:

[SolisCloud](https://www.soliscloud.com/)

Solis recommends logging out and logging back in after API access has been granted.

Navigate to:

```text
Service
└── API Management
```

Select **Activate Now**.

The activation process requires accepting the Solis API terms and completing a verification step. Solis will send a verification code to the email address associated with the account.

## 3. Obtain the API Credentials

After the API has been activated, the **API Management** section provides the credentials required to access the SolisCloud API.

The credentials consist of:

| Credential  | Description                                             |
| ----------- | ------------------------------------------------------- |
| `KeyID`     | Public identifier used when authenticating API requests |
| `KeySecret` | Secret used to authenticate API requests                |
| `API URL`   | Base URL used to communicate with the SolisCloud API    |

## 4. Verify API Access

Once the API credentials have been obtained, verify that they can be used successfully before configuring the application.

The **SolisCloud Platform API Document** is available from the API Management section of SolisCloud and provides information about the available API endpoints and authentication requirements.

For this project, the primary objectives of using the SolisCloud API are to:

* Retrieve the battery **State of Charge (SOC)**.
* Monitor the SOC and apply the project's defined logic.
* Send notifications when specific SOC thresholds or conditions are reached.
* Where supported, programmatically update the inverter configuration to enable **grid charging** during selected periods, such as overnight off-peak electricity periods.

The inverter used by this project is:

```text
S5-EH1P5K-L
```

The availability of specific API operations and remote-control functionality should be verified against the SolisCloud API documentation and the capabilities exposed for this inverter/account.

> **Important:** Solis distinguishes between **API access** and **remote-control access**. Having API access does not automatically mean that inverter settings can be changed through the API. Remote-control functionality and available settings may also depend on the account permissions and inverter configuration.

SolisCloud currently documents remote-control functionality including **Allow Grid Charging** and **Time-of-Use** charging/discharging settings for supported systems. These are relevant to the planned overnight battery-charging functionality of this project.

## 5. API Credentials and Plant Access

The API credentials are associated with the SolisCloud account rather than being generated specifically for an individual inverter.

Consequently, the credentials can be used to access the plants/devices available to that SolisCloud account, subject to the permissions associated with the account.

This is important if the SolisCloud account contains more than one plant or inverter.

## 6. Recommended Secret Handling

API credentials should **never** be committed to the repository.

For local development, use a `.env` file:

```dotenv
SOLIS_KEY_ID=your-key-id
SOLIS_KEY_SECRET=your-key-secret
SOLIS_API_URL=https://www.soliscloud.com:13333/
```

The `.env` file should be excluded from Git:

```gitignore
.env
```

For deployed environments, use the appropriate secret-management mechanism rather than storing the `KeySecret` directly in source code or configuration files committed to the repository.

## Official Solis Documentation

The following Solis resources provide the authoritative instructions for obtaining and activating API access:

* [Request API Access - SolisCloud](https://solis-service.solisinverters.com/en/support/solutions/articles/44002212561-request-api-access-soliscloud)
* [API Activation](https://solis-service.solisinverters.com/en/support/solutions/articles/44002507743-api-access-opened)
* [Solis Service Center](https://solis-service.solisinverters.com/)
* [SolisCloud](https://www.soliscloud.com/)
* [API Documentation Overview](https://developer.soliscloud.com/guide/)
* [The latest (Sep 2026) SolisCloud Platform API Document](https://oss.soliscloud.com/templet/SolisCloud%20Platform%20API%20Document%20V2.0.3.pdf)
