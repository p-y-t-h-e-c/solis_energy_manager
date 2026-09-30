# Solis Energy Manager

Solis Energy Manager is a notification application designed to help make day-to-day decisions about when to charge a home battery from the electricity grid.

## Background

I have a residential solar system managed by a **Solis S5-EH1P5K-L**, a 5 kW single-phase hybrid solar and battery storage inverter.

One of the inverter's capabilities is the ability to charge the batteries directly from the electricity grid. With **10 kWh of battery storage**, this creates an opportunity to charge the batteries during cheaper electricity periods and then use the stored energy throughout the day when electricity prices are higher.

There are a number of time-of-use electricity tariffs available in the UK that provide cheaper electricity during specific periods, for example:

* **Economy 7** — provides a number of cheaper electricity hours overnight alongside a higher daytime rate.
* **Octopus Go** — provides a period of cheaper electricity overnight.
* **Cosy Octopus** — provides multiple periods of cheaper electricity during the day.

These tariffs can make grid charging of the battery financially useful. However, deciding whether the battery should be charged on a particular night is not always straightforward.

## The Problem

From approximately **mid-September to mid-March**, there are periods when the amount of solar generation available during the following day can vary significantly. To make an informed decision about whether to charge the battery overnight, it is useful to know:

* the current battery state of charge;
* the expected solar exposure for the following day;
* when the available sunlight is expected to occur; and
* whether the predicted solar generation is likely to be sufficient to recharge the battery during the following day.

This is particularly relevant to my system because the majority of my solar panels face **east**. As a result, the timing of the available sunlight is important. A day with a reasonable amount of sunshine is not necessarily sufficient to recharge the battery if most of that sunlight occurs later in the day.

For example, if most of the expected sunny period occurs after around **14:00**, this may not provide enough useful solar generation to fully recharge the battery. This becomes particularly important during the shorter days between mid-September and mid-March.

## The Approach

It would be possible to manually check the Solis application for the current battery state and then use a separate weather application to look at the following day's forecast. However, this requires regularly checking multiple sources and making the decision manually.

To simplify this process, I developed **Solis Energy Manager** to bring the relevant information together and provide a simple notification with a summary of the expected conditions.

The application uses:

* **SolisCloud API** to retrieve live information about the solar and battery system, including the current battery state of charge.
* **Open-Meteo API** to retrieve weather and solar-related forecast information for the following day.
* Solar exposure and timing information to account for the orientation of the solar panels.
* Notification logic to combine this information and provide an indication of whether overnight battery charging should be considered.

The application currently runs at **16:00 each day** and sends the resulting summary by email. SMS notifications are also supported by the underlying design and could be enabled in the future.

## Why Notifications?

The main purpose of the application is convenience rather than replacing the existing Solis or weather applications.

I could manually open the Solis application, check the current battery level, open a weather application, review the forecast and then make the decision myself. However, I do not necessarily have the time to do this every day while dealing with other work and day-to-day activities.

Instead, Solis Energy Manager performs these checks automatically and sends me a notification at a convenient time. The notification brings the relevant information together into a single summary, allowing me to quickly understand the expected conditions for the following day and decide whether the battery should be charged overnight.

The application therefore acts as a small **decision-support and notification layer** on top of the existing Solis and weather services, rather than attempting to replace them.

## Table of Content

* [Project Setup](.docs/project_setup.md)
* [Solis API](.docs/solis_api.md)
* [Docker Deployment](.docs/docker_deployment.md)
* [GitHub Actions](.docs/github_actions.md)
* [Oracle VM Instance](.docs/oracle_vm_instance.md)
