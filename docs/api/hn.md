# Hacker News Search API (Algolia)

This API is built on top of Algolia Search's API and lets developers access Hacker News data programmatically via a REST API.

Base URL: `http://hn.algolia.com/api/v1`

## Endpoints

### GET /items/:id

Retrieve an item (story, comment, poll, etc.) by ID.

Example:

```
GET http://hn.algolia.com/api/v1/items/1
```

Sample response (abridged):

```json
{
  "id": 1,
  "created_at": "2006-10-09T18:21:51.000Z",
  "author": "pg",
  "title": "Y Combinator",
  "url": "http://ycombinator.com",
  "text": null,
  "points": 57,
  "parent_id": null,
  "children": [
    {
      "id": 15,
      "created_at": "2006-10-09T19:51:01.000Z",
      "author": "sama",
      "text": "\"the rising star of venture capital\" -unknown VC eating lunch on SHR",
      "points": 5,
      "parent_id": 1,
      "children": [
        {
          "id": 17,
          "created_at": "2006-10-09T19:52:45.000Z",
          "author": "pg",
          "text": "Is there anywhere to eat on Sandhill Road?",
          "points": 5,
          "parent_id": 15,
          "children": []
        }
      ]
    }
  ]
}
```

### GET /users/:username

Get user details.

Example:

```
GET http://hn.algolia.com/api/v1/users/pg
```

Sample response:

```json
{
  "username": "pg",
  "about": "PG's bio",
  "karma": 99999
}
```

### Search endpoints

- Search (sorted by relevance):  
  `GET http://hn.algolia.com/api/v1/search?query=...`

- Search by date (most recent first):  
  `GET http://hn.algolia.com/api/v1/search_by_date?query=...`

## Common query parameters

| Parameter         |                                                                                    Description | Type    |
| ----------------- | ---------------------------------------------------------------------------------------------: | ------- |
| `query=`          |                                                                                Full-text query | string  |
| `tags=`           |                                            Filter on a specific tag. See available tags below. | string  |
| `numericFilters=` | Filter on numerical fields (<, <=, =, >, >=). Fields: `created_at_i`, `points`, `num_comments` | string  |
| `page=`           |                                                                          Page number (0-based) | integer |
| `hitsPerPage=`    |                                                                     Number of results per page | integer |

Available tags:

- `story`, `comment`, `poll`, `pollopt`, `show_hn`, `ask_hn`, `front_page`
- `author_:USERNAME` (e.g. `author_pg`)
- `story_:ID` (e.g. `story_123`)

Tag logic:

- Tags are ANDed by default.
- Use parentheses to OR tags, e.g. `tags=author_pg,(story,poll)` → author=pg AND (type=story OR type=poll).

Pagination:

- Results are split into pages. Use `page=` and `hitsPerPage=` to iterate or increase page size.
- Response includes `page`, `nbHits`, `nbPages`, `hitsPerPage`.

## Examples

- All stories matching `foo`  
  `http://hn.algolia.com/api/v1/search?query=foo&tags=story`

- All comments matching `bar`  
  `http://hn.algolia.com/api/v1/search?query=bar&tags=comment`

- All URLs matching `bar`  
  `http://hn.algolia.com/api/v1/search?query=bar&restrictSearchableAttributes=url`

- Front page stories now  
  `http://hn.algolia.com/api/v1/search?tags=front_page`

- Last stories (by date)  
  `http://hn.algolia.com/api/v1/search_by_date?tags=story`

- Stories OR polls (by date)  
  `http://hn.algolia.com/api/v1/search_by_date?tags=(story,poll)`

- Comments since timestamp X (seconds)  
  `http://hn.algolia.com/api/v1/search_by_date?tags=comment&numericFilters=created_at_i>X`

- Stories between timestamp X and Y (seconds)  
  `http://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>X,created_at_i<Y`

- Stories by user `pg`  
  `http://hn.algolia.com/api/v1/search?tags=story,author_pg`

- Comments of story X  
  `http://hn.algolia.com/api/v1/search?tags=comment,story_X`

## Sample search response (abridged)

```json
{
  "hits": [
    {
      "title": "Y Combinator",
      "url": "http://ycombinator.com",
      "author": "pg",
      "points": 57,
      "num_comments": 2,
      "objectID": "1",
      "_tags": ["story"],
      "_highlightResult": {
        "title": {
          "value": "Y Combinator",
          "matchLevel": "none",
          "matchedWords": []
        },
        "url": {
          "value": "http://ycombinator.com",
          "matchLevel": "none",
          "matchedWords": []
        },
        "author": {
          "value": "<em>pg</em>",
          "matchLevel": "full",
          "matchedWords": ["pg"]
        }
      }
    }
    // ...more hits...
  ],
  "page": 0,
  "nbHits": 11,
  "nbPages": 1,
  "hitsPerPage": 20,
  "processingTimeMS": 1,
  "query": "pg",
  "params": "query=pg"
}
```

## Rate limits

Requests are limited to 10,000
