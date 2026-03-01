# Extração de URL de Vídeo - AnimesROLL

Este documento descreve o processo de extração da URL do vídeo do anime "Uruwashi no Yoi no Tsuki" (Episódio 1) disponível no site AnimesROLL.

## URL Alvo

```
https://anroll.tv/episodios/uruwashi-no-yoi-no-tsuki-episodio-1/
```

## Servidores Disponíveis

O site oferece 3 opções de servidor para assistir ao episódio:

| Opção | Servidor | Qualidade |
|-------|----------|-----------|
| 1 | Vidmoly | 1080p LEG |
| 2 | Abyss | 1080p LEG |
| 3 | Voe | 1080p LEG |

## Processo de Extração

### 1. Análise da Página Inicial

A página do episódio exibe uma lista de opções de servidor. Cada opção é um link que carrega um iframe com o player do servidor correspondente.

### 2. Comandos Playwright CLI Utilizados

A extração foi realizada utilizando o Playwright CLI. Abaixo estão os comandos e seletores utilizados:

#### Comandos Executados

```bash
# Abrir a página do episódio
playwright-cli open "https://anroll.tv/episodios/uruwashi-no-yoi-no-tsuki-episodio-1/"

# Obter snapshot da página para identificar elementos
playwright-cli snapshot

# Clicar na opção 1 (Vidmoly) - ID do elemento: e39
playwright-cli click e39

# Clicar na opção 2 (Abyss) - ID do elemento: e42
playwright-cli click e42

# Clicar na opção 3 (Voe) - ID do elemento: e45
playwright-cli click e45

# Obter URL do iframe do player
playwright-cli eval "document.querySelector('iframe').src"

# Verificar requisições de rede
playwright-cli network
```

#### Python - Extração da API

Também é possível extrair as URLs diretamente via API usando Python:

```python
import requests

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# API do AnimesROLL para obter URL do embed
# Formato: https://anroll.tv/wp-json/dooplayer/v2/{anime_id}/tv/{option}

# Opção 1 - Vidmoly
r1 = requests.get("https://anroll.tv/wp-json/dooplayer/v2/3929/tv/1", headers=headers)
print(r1.json())

# Opção 2 - Abyss
r2 = requests.get("https://anroll.tv/wp-json/dooplayer/v2/3929/tv/2", headers=headers)
print(r2.json())

# Opção 3 - Voe
r3 = requests.get("https://anroll.tv/wp-json/dooplayer/v2/3929/tv/3", headers=headers)
print(r3.json())
# Resultado: {"embed_url":"https:\/\/voe.sx\/e\/h7deo4gudj13","type":"iframe"}
```

#### Seletores e Elementos

| Elemento | ID ref | Descrição |
|---------|--------|------------|
| Opção 1 (Vidmoly) | `e39` | `#player-option-1` - Lista de opções do servidor |
| Opção 2 (Abyss) | `e42` | `#player-option-2` - Lista de opções do servidor |
| Opção 3 (Voe) | `e45` | `#player-option-3` - Lista de opções do servidor |
| Iframe do player | - | `iframe` - Player incorporado do servidor |

#### Estrutura do DOM (simplificado)

```html
<!-- Lista de opções de servidor -->
<ul class="player-options">
  <li id="player-option-1">
    <span>Opção 1 (Vidmoly) - 1080p LEG</span>
  </li>
  <li id="player-option-2">
    <span>Opção 2 (Abyss) - 1080p LEG</span>
  </li>
  <li id="player-option-3">
    <span>Opção 3 (Voe) - 1080p LEG</span>
  </li>
</ul>

<!-- Iframe do player (após clicar em uma opção) -->
<iframe id="player-iframe" src="https://voe.sx/e/h7deo4gudj13"></iframe>
```

#### Análise de Rede

Requisições de rede capturadas durante a interação:

```bash
# Requisição para API do player (Opção 3 - Voe)
GET https://anroll.tv/wp-json/dooplayer/v2/3929/tv/3

# Resposta:
# {"embed_url":"https:\/\/voe.sx\/e\/h7deo4gudj13","type":"iframe"}

# Requisição para API do player (Opção 1 - Vidmoly)
GET https://anroll.tv/wp-json/dooplayer/v2/3929/tv/1

# Requisição para API do player (Opção 2 - Abyss)
GET https://anroll.tv/wp-json/dooplayer/v2/3929/tv/2

#Requisição para o Master Playlist HLS (Vidmoly)
GET https://vdoc-3d-ccd-2.getromes.space/hls/,xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla,.urlset/master.m3u8
```

### 3. API do AnimesROLL

O AnimesROLL usa uma API interna para obter as URLs de embed dos servidores. O endpoint segue o padrão:

```
GET https://anroll.tv/wp-json/dooplayer/v2/{anime_id}/tv/{option}
```

Para este episódio:
- Anime ID: `3929`
- Opção 1 (Vidmoly): `/tv/1`
- Opção 2 (Abyss): `/tv/2`
- Opção 3 (Voe): `/tv/3`

**Resposta da API (Opção 3 - Voe):**
```json
{
  "embed_url": "https://voe.sx/e/h7deo4gudj13",
  "type": "iframe"
}
```

### 4. Identificação da URL do Vídeo

A URL do vídeo foi identificada através da análise das requisições de rede:

1. **Clicar na opção do servidor** - O clique em `e39`, `e42` ou `e45` carrega um iframe
2. **Capturar URL do iframe** - `document.querySelector('iframe').src`
3. **Analisar requisições de rede** - `playwright-cli network`

O iframe do Vidmoly fez uma requisição para o master playlist HLS que foi capturada nos logs de rede:

```
GET https://vdoc-3d-ccd-2.getromes.space/hls/,xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla,.urlset/master.m3u8
```

### 5. Análise dos Servidores

### 5. Análise dos Servidores

#### Vidmoly (Opção 1) - FUNCIONANDO

A URL do embed do Vidmoly leva a um player que utiliza HLS (HTTP Live Streaming).

A URL foi obtida através da análise de rede do Playwright, que mostrou a seguinte requisição:

```
GET https://vdoc-3d-ccd-2.getromes.space/hls/,xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla,.urlset/master.m3u8
```

Verificação com Python Requests:

```python
import requests

url = "https://vdoc-3d-ccd-2.getromes.space/hls/,xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla,.urlset/master.m3u8"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

r = requests.get(url, headers=headers, timeout=10)
print(r.status_code)  # 200
print(r.text)  # Master playlist content
```

**URL do Master Playlist:**
```
https://vdoc-3d-ccd-2.getromes.space/hls/,xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla,.urlset/master.m3u8
```

**Qualidade disponível:**
- 1080p (1600x900) - BANDWIDTH: 1538538

**Estrutura HLS:**
```
#EXTM3U
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1538538,RESOLUTION=1600x900
https://vdoc-3d-ccd-2.getromes.space/hls/xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla/index-v1-a1.m3u8
```

#### Abyss (Opção 2) - BLOQUEADO

O servidor Abyss está bloqueado (retorna 403 Forbidden):
```
https://abysscdn.com/?v=C-PgQzG0s
```

#### Voe (Opção 3) - REQUER JAVASCRIPT

O Voe usa proteção anti-scraping com:
- Redirecionamento JavaScript
- Verificação de contexto (iframe detection)
- Protección contra dev tools

A URL final do embed:
```
https://lancewhosedifficult.com/access/{token}?o=1
```

O player usa JWPlayer, mas a URL do vídeo não é exposta facilmente sem executar JavaScript.

## URL do Vídeo Extraída

### Opção Vidmoly (Recomendada)

**Master Playlist URL:**
```
https://vdoc-3d-ccd-2.getromes.space/hls/,xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla,.urlset/master.m3u8
```

**URL direta (1080p):**
```
https://vdoc-3d-ccd-2.getromes.space/hls/xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla/index-v1-a1.m3u8
```

## Como Reproduzir

### Com MPV
```bash
mpv "https://vdoc-3d-ccd-2.getromes.space/hls/,xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla,.urlset/master.m3u8"
```

### Com VLC
1. Abra o VLC
2. Media > Open Network Stream
3. Cole a URL do master playlist

### Comyt-dl (para download)
```bash
yt-dl "https://vdoc-3d-ccd-2.getromes.space/hls/,xqx2okt37nokjiqbtgas56irxrplxdz7vcbjefbzspcv5flkk5n7bs3bwgla,.urlset/master.m3u8"
```

## Notas

- As URLs podem expirar após um período
- O Vidmoly foi o único servidor funcional nesta extração
- O Abyss está completamente bloqueado
- O Voe requer execução JavaScript para obter o stream

## Ferramentas Utilizadas

- **Playwright CLI** - Automação de browser para interação com a página
- **Requests** - Requisições HTTP para análise de API e extração de URLs
- **Browser Developer Tools** - Análise de rede e DOM
