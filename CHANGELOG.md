# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e este projeto segue [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-02-06

### Added

#### 🎬 Airing Episodes (Novos Episódios)
- Nova feature "Novos Episódios" no menu AniList que mostra animes em transmissão
- Lista apenas animes da lista "Watching" que têm novos episódios no ar
- Calcula e exibe o gap (quantos episódios você está atrasado)
- Ordena por urgência: animes com maior atraso aparecem primeiro
- Mostra score do AniList para cada anime
- Formato: "Anime Title - Ep X aired, você viu Y (Z atrasado) ⭐Score%"
- Integração seamless: selecione anime para começar playback no episódio certo

#### 📂 Biblioteca Local (Download & Offline Watching)
- Nova tab "📂 Biblioteca Local" no menu principal
- Baixe episódios para assistir depois (sem necessidade de internet)
- Range flexível para downloads: `5` (ep 5), `1-12` (eps 1-12), `5-` (ep 5+), `-12` (até ep 12)
- Downloads paralelos configuráveis (1-16 simultâneos)
- Progresso salvo localmente em JSON
- Sincronização automática com AniList após playback
- Organização por anime em `~/.local/share/ani-tupi/anime/`

#### 🔍 Busca Incremental com Histórico
- Busca progressiva que refina resultados conforme você digita
- Menu interativo mostrando histórico de buscas anteriores
- Melhor precisão para títulos longos ou ambíguos
- Função de busca normalizada para comparação
- Stop early optimization quando confiança > 95%

#### 🔧 Melhorias de Robustez
- Validação de fontes por prioridade (AnimesDigital > AnimesFire)
- Tratamento correto de fallback source que retorna lista vazia
- Homepage incremental search para AnimesDigital (encontra episódios novos)
- Suporte a episodes descobertos dinamicamente
- Deduplicação de URLs na homepage search

### Fixed

- **AnimesDigital Fallback Source**: Agora valida se a fonte retorna capítulos não-vazios antes de aceitar
- **AnimesDigital ?odr=1 Parameter**: Documentado que é MANDATORY para exibir episódios
- **Episode Ordering**: Episódios agora são sempre ordenados por número, não por descoberta
- **Homepage Search Matching**: Fuzzy matching agora tem thresholds apropriados (70% single-word, 65% multi-word, 75% final validation)
- **URL Deduplication**: Homepage search agora deduplica URLs vistas
- **Episode Priority Order**: Sistema respeita `settings.plugins.priority_order` coletando todas fontes e retornando primeira por prioridade

### Changed

- README refatorado: instalação movida para topo (após demo)
- Changelog estruturado em formato mais legível
- Documentação de features organizadas por categoria (Anime, Manga, AniList, Geral)
- Download handler refatorado para evitar re-fetching de chapters já carregados

### Technical Details

#### Airing Episodes Architecture
- **Service**: `AiringEpisodesService` - lógica de negócio
- **GraphQL Query**: `MediaListCollection(status: CURRENT)` com `nextAiringEpisode`
- **Model**: `AiringAnimeEntry` - dados tipados para exibição
- **Tests**: 17 testes de service, 11 de scraper search, 100% passing

#### Local Library Architecture
- **Service**: `LocalAnimeService` - gerencia biblioteca local
- **Download Service**: `AnimeDownloadService` - orquestra downloads com fila paralela
- **Models**: `DownloadedEpisode`, `DownloadedAnime` - Pydantic validados
- **Storage**: `~/.local/share/ani-tupi/anime/` (XDG standard)
- **History**: `~/.local/state/ani-tupi/anime_downloads.json`
- **Tests**: 51 testes com 100% passing, sem testes live network

#### Incremental Search Architecture
- **Parser**: Normalização de títulos (remove "Dublado", "Legendado", etc)
- **Matching**: Fuzzy matching com thresholds progressivos
- **History**: Menu mostra buscas anteriores com navegação
- **Optimization**: Stop-early quando confiança atinge limites

---

## [0.2.0] - 2024-12-25

### Added

#### 🔄 Switch Source During Playback
- Opção "🔄 Trocar fonte" no menu pós-episódio
- Alternar entre versões dublada/legendada
- Suporta diferentes scrapers (AnimeFire, AnimesDigital, etc)
- Mostra todas as variações encontradas para o anime base
- Disponível em busca normal e fluxo AniList

#### 🎵 Manga CLI Refactor
- Refatoração completa seguindo padrão MVCP (Model-View-Controller-Plugin)
- Service layer MangaDex com error handling e cache
- Substituição de `input()` por Rich + InquirerPy menus
- Loading spinners para API calls
- Histórico de leitura persistido em JSON (`manga_history.json`)
- Dica "⮕ Retomar" mostrando último capítulo lido
- Configuração centralizada com Pydantic (`config.py`)
- Pydantic data models para tipagem forte
- Cache de capítulos (24h padrão, configurável)
- Suporte a múltiplos idiomas (pt-br, en, ja padrão)

#### ⚡ Performance Improvements
- Cache de episódios: carrega lista instantaneamente na segunda visita
- Cache de scrapers: resultados de busca salvos localmente
- Migração de Textual para Rich + InquirerPy: TUI 65% menor, 10x mais rápido

#### 🎉 AniList Enhancements
- Adição automática de anime à lista "Watching" ao começar a assistir
- Menu de conta AniList com perfil e estatísticas
- Navegação melhorada: ESC para voltar, Q para sair
- Títulos bilíngues (romaji + inglês)

### Fixed

- FileNotFoundError ao executar CLI de fora da pasta do projeto
- Crash ao usar cache de episódios em alguns casos
- Formatação e mensagens de UX

### Changed

- Aplicação completa de linting Ruff
- Reorganização de imports
- Documentação refatorada com OpenSpec

---

## [0.1.0] - 2024-10-15

### Added

- ✅ Sistema de plugins para múltiplos scrapers
- ✅ Integração com mpv para reprodução de vídeos
- ✅ Menu em português brasileiro com curses
- ✅ Histórico local de episódios assistidos
- ✅ Suporte a modo debug
- ✅ Build com PyInstaller para executável standalone
- ✅ Instalação via UV tool como comando global
- ✅ Integração básica com AniList (leitura de listas)
- ✅ Sistema de cache de episódios
- ✅ Suporte a múltiplos scrapers (AnimeFire, AnimesonlineCC)

---

## Tipos de Mudança

- **Added**: Nova funcionalidade
- **Changed**: Mudança em funcionalidade existente
- **Fixed**: Correção de bug
- **Removed**: Funcionalidade removida
- **Security**: Correção de vulnerabilidade
- **Deprecated**: Funcionalidade que será removida em breve
- **Technical**: Mudanças internas/refatoração sem impacto ao usuário

---

## Como Contribuir

Para sugerir mudanças, abra uma issue ou pull request.

Changelog será atualizado para cada release significativa.

[0.3.0]: https://github.com/levyvix/ani-tupi/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/levyvix/ani-tupi/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/levyvix/ani-tupi/releases/tag/v0.1.0
