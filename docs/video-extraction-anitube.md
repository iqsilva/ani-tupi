# Extração de Dados - AniTube

Este documento descreve o processo de extração de dados do site AniTube, incluindo busca de animes, lista de episódios e URL do vídeo.

## URL Alvo

```
https://www.anitube.news/?s=jujutsu+kaisen
```

---

## 1. Busca de Animes

### 1.1 Método: WordPress REST API

O AniTube é construído sobre WordPress e expõe uma REST API para busca de conteúdo.

**Endpoint:**
```
GET https://www.anitube.news/wp-json/wp/v2/posts?search={query}&per_page=20
```

**Parâmetros:**
| Parâmetro | Descrição |
|-----------|-----------|
| `search` | Termo de busca (ex: "jujutsu kaisen") |
| `per_page` | Número de resultados por página |
| `page` | Número da página |

**Exemplo de Requisição:**
```python
import requests

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Busca por anime
r = requests.get(
    "https://www.anitube.news/wp-json/wp/v2/posts?search=jujutsu+kaisen&per_page=20",
    headers=headers
)

results = r.json()
for post in results:
    print(f"Título: {post['title']['rendered']}")
    print(f"URL: {post['link']}")
    print()
```

**Resposta:**
```json
[
  {
    "id": 1044657,
    "title": {"rendered": "Jujutsu Kaisen 3 (Dublado) – Episódio 06"},
    "link": "https://www.anitube.news/video/1044657/",
    "date": "2026-02-26T15:21:53"
  },
  ...
]
```

### 1.2 Resultado da Busca "jujutsu+kaisen"

| # | Título | URL |
|---|--------|-----|
| 1 | Jujutsu Kaisen 3 Dublado – Todos os Episódios | https://www.anitube.news/video/1037840/ |
| 2 | Jujutsu Kaisen 3 – Todos os Episódios Legendado | https://www.anitube.news/video/1031725/ |
| 3 | Jujutsu Kaisen (Dublado) – Todos os Episódios | https://www.anitube.news/970484b002 |
| 4 | Jujutsu Kaisen 2 (Dublado) – Todos os Episódios | https://www.anitube.news/970537b002 |
| 5 | Jujutsu Kaisen – Todos os Episódios Legendado | https://www.anitube.news/897019b002 |
| 6 | Jujutsu Kaisen 2 – Todos Episódios Legendado | https://www.anitube.news/919956b001 |

---

## 2. Lista de Episódios

### 2.1 Estrutura da Página de Anime

A página de lista de episódios (ex: https://www.anitube.news/video/1037840/) contém:

**Elementos do DOM:**

| Elemento | ID/Seletor | Descrição |
|----------|------------|-----------|
| Título | `h1` | Título do anime |
| Lista de Episódios | `.episode-list li` | Container de episódios |
| Episódio | `a` dentro da lista | Link para página do episódio |
| Imagem | `img` | Thumbnail do anime |

**Exemplo de Estrutura HTML:**
```html
<h1>Jujutsu Kaisen 3 Dublado – Todos os Episódios</h1>

<div class="episode-list">
  <ul>
    <li>
      <a href="https://www.anitube.news/video/1037850/">
        Jujutsu Kaisen 3 (Dublado) – Episódio 01
      </a>
    </li>
    <li>
      <a href="https://www.anitube.news/video/1037852/">
        Jujutsu Kaisen 3 (Dublado) – Episódio 02
      </a>
    </li>
    ...
  </ul>
</div>
```

### 2.2 Comandos Playwright CLI Utilizados

```bash
# Abrir página de busca
playwright-cli open "https://www.anitube.news/?s=jujutsu+kaisen"

# Clicar no resultado (Jujutsu Kaisen 3 Dublado)
playwright-cli click e36

# Capturar snapshot da página
playwright-cli snapshot
```

**Seletores e Elementos:**

| Elemento | ID ref | Seletor CSS |
|-----------|--------|-------------|
| Resultado 1 | `e36` | `.result-item a` |
| Resultado 2 | `e42` | `.result-item:nth-child(2) a` |
| Lista de episódios | `e68` | `.episode-list` |
| Episódio 01 | `e69` | `.episode-list a:nth-child(1)` |
| Episódio 02 | `e70` | `.episode-list a:nth-child(2)` |

### 2.3 Episódios Encontrados (Jujutsu Kaisen 3 Dublado)

| # | Título | URL |
|---|--------|-----|
| 1 | Jujutsu Kaisen 3 (Dublado) – Episódio 01 | https://www.anitube.news/video/1037850/ |
| 2 | Jujutsu Kaisen 3 (Dublado) – Episódio 02 | https://www.anitube.news/video/1037852/ |
| 3 | Jujutsu Kaisen 3 (Dublado) – Episódio 03 | https://www.anitube.news/video/1039703/ |
| 4 | Jujutsu Kaisen 3 (Dublado) – Episódio 04 | https://www.anitube.news/video/1041250/ |
| 5 | Jujutsu Kaisen 3 (Dublado) – Episódio 05 | https://www.anitube.news/video/1042682/ |
| 6 | Jujutsu Kaisen 3 (Dublado) – Episódio 06 | https://www.anitube.news/video/1044657/ |

---

## 3. URL do Vídeo

### 3.1 Método: Análise de Rede

A URL do vídeo é obtida através de uma requisição HLS (HTTP Live Streaming).

**Requisição capturada nos logs de rede:**
```
GET https://cdn-s01.mywallpaper-4k-image.net/stream/j/jujutsu-kaisen-3-dublado/01.mp4/index.m3u8
```

**Status:** 200 OK

### 3.2 API AniVideo

O site usa uma API intermediária para fornecer o vídeo:

**Endpoint:**
```
GET https://api.anivideo.net/videohls.php?d={encoded_url}
```

**Parâmetro:**
| Parâmetro | Descrição |
|-----------|-----------|
| `d` | URL codificada do CDN (URL encoded) |

**Exemplo:**
```python
import urllib.parse

cdn_url = "https://cdn-s01.mywallpaper-4k-image.net/stream/j/jujutsu-kaisen-3-dublado/01.mp4/index.m3u8"
encoded = urllib.parse.quote(cdn_url, safe="")

api_url = f"https://api.anivideo.net/videohls.php?d={encoded}"
# https://api.anivideo.net/videohls.php?d=https%3A%2F%2Fcdn-s01.mywallpaper-4k-image.net%2Fstream%2Fj%2Fjujutsu-kaisen-3-dublado%2F01.mp4%2Findex.m3u8
```

### 3.3 URLs do Vídeo Extraídas

**Master Playlist (HLS):**
```
https://cdn-s01.mywallpaper-4k-image.net/stream/j/jujutsu-kaisen-3-dublado/01.mp4/index.m3u8
```

**Estrutura HLS:**
```
#EXTM3U
#EXT-X-TARGETDURATION:10
#EXT-X-ALLOW-CACHE:YES
#EXT-X-PLAYLIST-TYPE:VOD
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:1
#EXTINF:10.000,
https://cdn-s01.mywallpaper-4k-image.net/stream/j/jujutsu-kaisen-3-dublado/01.mp4/seg-1-v1-a1.webp
#EXTINF:10.000,
https://cdn-s01.mywallpaper-4k-image.net/stream/j/jujutsu-kaisen-3-dublado/01.mp4/seg-2-v1-a1.webp
...
```

### 3.4 Padrão de URL de Vídeo

**Padrão identificado:**
```
https://cdn-s01.mywallpaper-4k-image.net/stream/{primeira_letra}/{nome_anime}/{numero_episodio}.mp4/index.m3u8
```

**Exemplo:**
- Anime: `jujutsu-kaisen-3-dublado`
- Episódio: `01`
- URL: `https://cdn-s01.mywallpaper-4k-image.net/stream/j/jujutsu-kaisen-3-dublado/01.mp4/index.m3u8`

### 3.5 Comandos Playwright CLI

```bash
# Abrir página do episódio
playwright-cli open "https://www.anitube.news/video/1037850/"

# Capturar requisições de rede
playwright-cli network
```

---

## 4. Resumo das APIs

### 4.1 WordPress REST API

| Endpoint | Descrição |
|----------|-----------|
| `https://www.anitube.news/wp-json/wp/v2/posts?search={query}` | Busca de posts/animes |
| `https://www.anitube.news/wp-json/wp/v2/categories` | Lista de categorias |
| `https://www.anitube.news/wp-json/wp/v2/tags` | Lista de tags |

### 4.2 API de Vídeo

| Endpoint | Descrição |
|----------|-----------|
| `https://api.anivideo.net/videohls.php?d={url}` | API intermediária de vídeo |
| `https://cdn-s01.mywallpaper-4k-image.net/stream/...` | CDN de streaming |

---

## 5. Como Reproduzir

### Com MPV
```bash
mpv "https://cdn-s01.mywallpaper-4k-image.net/stream/j/jujutsu-kaisen-3-dublado/01.mp4/index.m3u8"
```

### Com VLC
1. Abra o VLC
2. Media > Open Network Stream
3. Cole a URL do master playlist

---

## 6. Notas

- As URLs de vídeo podem expirar após um período
- O site usa proteção por redirecionamento JavaScript
- O player é嵌入 em um iframe
- O CDN usa formato HLS com segmentos .webp

---

## 7. Ferramentas Utilizadas

- **Playwright CLI** - Automação de browser
- **Requests** - Requisições HTTP
- **Python** - Processamento de dados
