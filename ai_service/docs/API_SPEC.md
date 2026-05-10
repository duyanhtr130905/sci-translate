# SCI Translate AI Service API Spec

Base URL: `http://localhost:8000`

This document covers the 3 endpoints handed off from TV2 to TV3.

## 1. Health Check

`GET /health/`

Checks whether the AI service is running.

### Response 200

```json
{
  "status": "ok",
  "service": "SCI Translate AI Service"
}
```

## 2. Translate Text

`POST /translate/`

Translates scientific text between English and Vietnamese. If `source_lang` or
`target_lang` is omitted, the service detects the source language and chooses
the opposite target language.

### Request Body

```json
{
  "text": "Machine learning models can improve translation quality.",
  "source_lang": "en",
  "target_lang": "vi"
}
```

### Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `text` | string | Yes | Input text to translate. Must not be empty. |
| `source_lang` | string or null | No | Source language code, usually `en` or `vi`. |
| `target_lang` | string or null | No | Target language code, usually `vi` or `en`. |

### Response 200

```json
{
  "original_text": "Machine learning models can improve translation quality.",
  "translated_text": "Cac mo hinh hoc may co the cai thien chat luong dich.",
  "source_lang": "en",
  "target_lang": "vi"
}
```

### Error Responses

`400 Bad Request`

Returned when `text` is empty after trimming.

```json
{
  "detail": "Empty input"
}
```

`422 Unprocessable Entity`

Returned by FastAPI when the request body is invalid or the required `text`
field is missing.

## 3. Terms

`GET /terms/`

Returns the current scientific term examples exposed by the AI service.

### Response 200

```json
{
  "terms": [
    {
      "en": "machine learning",
      "vi": "hoc may"
    },
    {
      "en": "deep learning",
      "vi": "hoc sau"
    },
    {
      "en": "transformer",
      "vi": "mo hinh bien ap"
    }
  ]
}
```

## OpenAPI

The exported OpenAPI document is stored at:

`ai_service/docs/openapi.json`
