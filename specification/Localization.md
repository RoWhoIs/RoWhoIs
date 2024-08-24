# RoWhoIs Localization

## Introduction

Because RoWhoIs is used by thousands of users across the globe daily, it's important that we take into consideration the localization of users. Some may hardly speak English, or others are uncomfortable with the language.

## Objective

To provide automatic translations for users with a non-english localization.

## Requirements

Each public-facing string must be passed through the localization library, which takes a text of string and compares it to a list of translations for the correct language.

## Design

This function is located in the `utils` library. It is an IO blocking function.

```python
localize(interaction: hikari.interaction, message: str) -> str
```


## Usage

To translate a message is simple. You pass the interaction and the string requested. From there, the function will return a string. If the localization has been implemented, it will return the translated string. If not, it will return the string passed to it.

### Example

**Usage**

Mockup data: Localization is Danish.

```python
import utils

utils.localize(interaction, "Hello World!")
```

**Output**
```python
"Hej Verrden!"
```

## Error Handling

If any error is encountered during the localization, it will return the string provided. This function will never raise an exception.


