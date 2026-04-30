# 🎬 ani-tupi

Assista anime e leia mangá direto do terminal sem anúncios! Interface CLI em português brasileiro com integração AniList.

> Estava cansado de anúncios, o ani-cli não tinha conteúdo em português brasileiro e não havia leitor de mangá decente no terminal, então criei esta ferramenta.

## 📺 Demo no YouTube
[![Demo](https://img.youtube.com/vi/eug6gKLTD3I/maxresdefault.jpg)](https://youtu.be/eug6gKLTD3I)

## 📋 Requisitos

- **Python 3.12+** (obrigatório)
- **mpv** (player de vídeo)
- **Zathura** (leitor de PDF para mangá - recomendado)
- **Firefox** (opcional, para alguns scrapers)
- **git** (para clonar o repositório)

### Instalando dependências

#### Linux (Arch)
```bash
# Instalar dependências do sistema
sudo pacman -S python mpv zathura firefox git libxml2 libvpx flite webkit2gtk-4.1
```

#### Linux (Ubuntu/Debian)
```bash
# Instalar dependências do sistema
sudo apt install python3 mpv zathura firefox git libxml2 libvpx libflite1 webkit2gtk-4.1
```

#### Linux (Fedora)
```bash
# Instalar dependências do sistema
sudo dnf install python3 mpv zathura firefox git libxml2 libvpx flite webkit2gtk-4.1
```

#### macOS
```bash
# Instalar dependências do sistema
brew install python@3.12 mpv zathura firefox git
```

#### Windows
Recomendamos usar [Chocolatey](https://chocolatey.org/install):
```powershell
# Como administrador
choco install python mpv zathura firefox git

uv run playwright install
```

**Nota:** Zathura é primariamente para Linux. No Windows, o sistema detectará automaticamente outros leitores de PDF instalados (Adobe Reader, SumatraPDF, etc).

## 🚀 Instalação Rápida

### Instalação com Um Comando (Recomendado)

A forma mais fácil de instalar - execute apenas um comando:

```bash
curl -sSL https://raw.githubusercontent.com/levyvix/ani-tupi/master/install.sh | bash
```

**O instalador faz automaticamente:**
- ✅ Detecta seu sistema (Linux, macOS, WSL)
- ✅ Verifica dependências (git, Python 3.12+)
- ✅ Instala UV se necessário
- ✅ Clona o repositório
- ✅ Instala ani-tupi como CLI global
- ✅ Configura o PATH automaticamente

**Requisitos do instalador:**
- `curl` - para baixar o script
- `git` - para clonar o repositório
- `Python 3.12+` - será detectado automaticamente

---

## ⚡ Primeiros Passos - Comandos Essenciais

Após instalar, estes são seus primeiros comandos:

```bash
# 1. Buscar e assistir anime
ani-tupi

# 2. Continuar último anime (salvo no histórico)
ani-tupi --continue-watching
ani-tupi -c

# 3. Buscar anime específico
ani-tupi --query "dandadan"
ani-tupi -q "dandadan"

# 4. Configurar AniList (sincronização automática)
ani-tupi anilist auth      # Login (apenas uma vez)
ani-tupi anilist           # Navegar listas + trending

# 5. Ler mangá
manga-tupi

# 6. Modo debug (mostra logs detalhados)
ani-tupi --debug

# 7. Ajuda
ani-tupi --help
```

## ⚙️ Configurar pela CLI

Agora você pode configurar o `ani-tupi` sem editar `models/config.py`:

```bash
ani-tupi config
```

No menu `ani-tupi config`:
- cada categoria representa uma classe de settings (`AnilistSettings`, `CacheSettings`, etc.)
- você escolhe a chave com `valor atual + descrição` do que ela controla
- antes de editar, a CLI mostra a documentação daquela configuração
- você informa o novo valor e confirma salvamento
- as alterações são persistidas no usuário em `~/.config/ani-tupi/settings.json`

### Precedência de configuração

O carregamento segue esta ordem:

1. Variáveis de ambiente (`ANI_TUPI__...`)
2. Configuração salva via `ani-tupi config`
3. Valores padrão da aplicação

Se uma chave tiver variável de ambiente ativa, o menu mostra aviso de precedência.

**💡 Dica para melhores resultados de busca:**
Tente usar o nome do anime em japonês ou romaji para maior precisão. Por exemplo:
- Em vez de "Attack on Titan", tente "Shingeki no Kyojin"
- Em vez de "My Hero Academia", tente "Boku no Hero Academia"
- Em vez de "Demon Slayer", tente "Kimetsu no Yaiba"
- Em vez de "Jujutsu Kaisen", mantenha como está (já é o título original)

---

### Atalhos Durante Reprodução

| Atalho | Ação |
|--------|------|
| `Shift+N` | Próximo episódio |
| `Shift+P` | Episódio anterior |
| `Shift+A` | Ativar auto-play |

---

## ✨ Features

### 🎬 Novos Episódios (AniList)
- Mostra animes com episódio novo e quanto você está atrasado
- Ordena por urgência e permite abrir para assistir direto
- Mantém títulos recém-finalizados por 60 dias

### 🏠 Biblioteca Local (Offline)
- Baixe episódios e organize por anime
- Suporta range de download (`5`, `1-12`, `5-`, `-12`)
- Paralelismo configurável para acelerar downloads

**Configuração rápida:**
```bash
export ANI_TUPI__ANIME__DOWNLOAD_DIRECTORY="~/Videos/Anime"
export ANI_TUPI__ANIME__MAX_PARALLEL_DOWNLOADS=4
export ANI_TUPI__ANIME__VIDEO_FORMAT="mp4"
```

---

## ✨ Integração com AniList (Recomendado!)

A integração com [AniList.co](https://anilist.co) permite sincronizar automaticamente seu progresso ao assistir anime e ler mangá.

### 📺 Anime
- 📈 **Trending** - Descubra os animes mais populares do momento
- 📺 **Watching** - Continue de onde parou (lista AniList)
- 📋 **Planning** - Veja animes que você planeja assistir
- ✅ **Completed** - Histórico de animes completos
- 🔄 **Sincronização automática** - Progresso atualiza no AniList após cada episódio
- 📝 **Adição automática à Watching** - Adiciona anime à sua lista ao começar a assistir

### 📚 Manga
- 📚 **Trending Manga** - Descubra os mangás mais populares do momento
- 📖 **Reading** - Acesse sua lista "Lendo" do AniList
- 🔄 **Sincronização de capítulos** - Atualiza progresso no AniList após confirmar leitura
- 📋 **Status unificados** - Veja animes e mangás juntos nas listas

### 💾 Recursos
- **Mapeamento inteligente** - Lembra do título correto para cada anime/mangá
- **Cache inteligente** - Carrega listas instantaneamente
- **Menu de conta** - Veja seu perfil e estatísticas

**Setup rápido:**
```bash
ani-tupi anilist auth      # Login (apenas uma vez)
ani-tupi anilist           # Navegar listas + trending
```

---

## 📖 Ler Mangá

Leia mangá do MangaDex direto do terminal com integração AniList!

**Comando:** `manga-tupi`

**Fluxo rápido:**
1. Abra `manga-tupi`
2. Digite nome do manga (fuzzy search automática)
3. Escolha capítulo
4. Leia no seu leitor PDF favorito
5. Progresso sincroniza automaticamente com AniList

**Leitores suportados:** Zathura (⭐ recomendado), Evince, Okular, MuPDF, macOS Preview, xdg-open

**Configuração:**
```bash
export ANI_TUPI__MANGA__PDF_READER=zathura
export ANI_TUPI__MANGA__OUTPUT_DIRECTORY=~/Mangas
export ANI_TUPI__MANGA__CACHE_DURATION_HOURS=48
```

---

### Troubleshooting

**Token expirou:**
```bash
ani-tupi anilist auth  # Faça login novamente
```

**Sincronização lenta:**
```bash
ani-tupi --debug  # Ver logs detalhados
```

---

### Modo Desenvolvimento

Se está desenvolvendo (sem instalação global):

```bash
uv run ani-tupi              # Executar
uv run main.py --debug       # Com debug
uv run main.py -q "naruto"   # Buscar direto
```

## 🔧 Para Desenvolvedores

### Estrutura do Projeto
```
ani-tupi/
├── main.py              # Entry point para anime
├── manga_tupi.py        # Entry point para mangá (refatorado)
├── manga_service.py     # Service layer MangaDex (NEW)
├── loader.py            # Sistema de plugins
├── repository.py        # Repositório de dados
├── menu.py              # Interface do menu (Rich + InquirerPy)
├── loading.py           # Loading spinners (Rich)
├── video_player.py      # Integração com mpv
├── models.py            # Pydantic data models (anime + manga)
├── config.py            # Configuração centralizada (Pydantic)
├── anilist.py           # Cliente AniList GraphQL
├── anilist_menu.py      # Menu AniList
├── scraper_cache.py     # Cache de scrapers
├── plugins/             # Plugins de scraping
│   ├── animefire.py
│   └── animesonlinecc.py
├── install-cli.py       # Instalador CLI global (principal)
├── monitor-actions.sh   # Monitor GitHub Actions
├── .github/workflows/   # CI/CD automático
│   ├── ci.yml           # Validação rápida
│   ├── build-test.yml   # Testes de build
│   └── release.yml      # Releases automáticas
└── pyproject.toml       # Configuração do projeto
```

### Comandos Úteis

```bash
# Instalar/Reinstalar CLI global
python3 install-cli.py
# ou: uv tool install --force .

# Desinstalar CLI global
uv tool uninstall ani-tupi

# Instalar dependências (desenvolvimento)
uv sync

# Adicionar nova dependência
uv add nome-do-pacote

# Adicionar dependência de desenvolvimento
uv add --dev nome-do-pacote
```

### Por que UV?

[UV](https://github.com/astral-sh/uv) é um gerenciador de pacotes Python extremamente rápido:
- ⚡ 10-100x mais rápido que pip
- 🔒 Lock file determinístico (`uv.lock`)
- 📦 Gerenciamento de venv automático
- 🌍 Multiplataforma (Linux, macOS, Windows)
- 🚀 Instalação zero-config

## 🐛 Problemas Conhecidos

### AnimesDigital falha: "Executable doesn't exist at /home/..."

**Causa:** Playwright browser binaries não estão instalados ou faltam dependências do sistema.

**Solução:**

```bash
# 1. Instale os binários do Playwright
uv run playwright install

# 2. Instale dependências do sistema para seu OS
```

**Para Arch Linux:**
```bash
sudo pacman -S libxml2 libvpx flite webkit2gtk-4.1 xdg-utils
```

**Para Ubuntu/Debian:**
```bash
sudo apt install libxml2 libvpx libflite1 webkit2gtk-4.1 xdg-utils
```

**Para Fedora:**
```bash
sudo dnf install libxml2 libvpx flite webkit2gtk-4.1 xdg-utils
```

**Para macOS:**
```bash
brew install libxml2 libvpx flite webkit2gtk
```

Depois de instalar, teste:
```bash
uv run python -c "from playwright.sync_api import sync_playwright; print('✓ Playwright funcionando')"
```

### "FileNotFoundError" ao salvar histórico
Corrigido na versão 0.1.0+. Atualize para a versão mais recente.

### MPV não abre
Verifique se o mpv está instalado:
```bash
mpv --version
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma issue ou pull request.

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📄 Licença

GPL-3.0 - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🎓 Propósito Educacional

**Este projeto é fornecido exclusivamente para fins educacionais e de pesquisa.**

ani-tupi foi desenvolvido como uma ferramenta didática para demonstrar:
- Arquitetura de aplicações em Python (MVCP)
- Web scraping e parsing de HTML
- Integração com APIs GraphQL
- Desenvolvimento de TUIs em Python
- Sistemas de plugins extensíveis
- Gestão de cache e requisições assíncronas

### Bases Legais para Manutenção Pública

Este projeto é mantido publicamente com base nas seguintes disposições legais:

#### 🇧🇷 Legislação Brasileira

**Lei Federal Nº 9.610/98 (Lei de Direitos Autorais) - Art. 46:**
> "Não constitui ofensa aos direitos autorais a utilização de obra intelectual em situações especificadas em lei, quando autorizada pelo titular dos direitos ou quando não há restrição ao direito de usar... **para fins de estudo ou pesquisa**..."

- **Art. 46, IV**: Permite reprodução para "fins exclusivamente escolares ou acadêmicos"
- **Art. 46, VIII**: Permite "o apanhado de trechos de obras, para fins de citação ou comentário crítico, desde que não represente concorrência com a exploração normal da obra..."

#### 🌍 Legislação Internacional

**DMCA (Digital Millennium Copyright Act) - Seção 1201(d):**
> "Para fins de segurança, pesquisa ou educação, a Biblioteca do Congresso pode examinar e autorizar contorno de proteção tecnológica..."

**Diretiva Europeia 2001/29/EC (Diretiva de Copyright):**
- Artigo 5(3) permite reprodução para fins de ilustração para fins educacionais
- Artigo 9 permite reprodução limitada para pesquisa

**Convenção de Berna (Tratado Internacional):**
- Artigo 10 permite uso de obras para fins educacionais e de pesquisa

#### ⚖️ Princípio Legal Aplicável: Fair Use / Uso Justo

Este projeto se beneficia do princípio de "Fair Use" (uso justo), que permite uso de conteúdo protegido quando:

1. **Propósito**: ✅ Educacional, não comercial
2. **Natureza**: ✅ Ferramenta de aprendizado técnico
3. **Quantidade**: ✅ Mínima necessária para demonstrar conceitos
4. **Impacto de Mercado**: ✅ Sem prejuízo comercial aos titulares originais

### Orientações de Uso

Este projeto é destinado para:
- ✅ **Aprendizado**: Estude como construir web scrapers e TUIs
- ✅ **Pesquisa**: Analise técnicas de integração com APIs
- ✅ **Educação**: Use como referência em cursos de Python
- ✅ **Desenvolvimento**: Base para seus próprios projetos educacionais

Este projeto **não é destinado para**:
- ❌ Redistribuição comercial de conteúdo
- ❌ Substituição dos serviços legítimos de streaming
- ❌ Contorno de proteções de direitos autorais com fins comerciais

### Aviso Legal

Ao usar este projeto, você concorda que:
- É responsável pela conformidade com as leis locais
- Compreende que este é um projeto educacional
- Não usará para fins comerciais ou prejudiciais
- Respeitará os direitos dos detentores de conteúdo

Para questões legais específicas em sua jurisdição, consulte um advogado especializado em direitos autorais.

## 🙏 Agradecimentos

- Comunidade anime brasileira
- Desenvolvedores do mpv
- Projeto ani-cli (inspiração)

---

## 📝 Changelog

### v0.3.0 (Fevereiro 2025) - Airing Episodes & Local Library

**🎬 Airing Episodes (Novos Episódios)**
- ✅ Novo tab "🎬 Novos Episódios" no menu AniList
- ✅ Lista animes em transmissão com gap de episódios
- ✅ Ordena por urgência (maior atraso primeiro)
- ✅ Mostra score e quanto você está atrasado
- ✅ Integração seamless com playback

**📂 Biblioteca Local (Download & Offline)**
- ✅ Tab "📂 Biblioteca Local" no menu principal
- ✅ Baixe episódios para assistir depois
- ✅ Range flexível: `5`, `1-12`, `5-`, `-12`
- ✅ Downloads paralelos configuráveis (1-16)
- ✅ Salva progresso local persistentemente
- ✅ Sincronização com AniList após playback

**🔍 Busca Incremental & Histórico**
- ✅ Busca progressiva com refinamento automático
- ✅ Histórico de buscas com navegação
- ✅ Melhor precisão para títulos ambíguos
- ✅ Menu inteligente para múltiplos resultados

**🔧 Melhorias de Robustez**
- ✅ Validação de fontes por prioridade (AnimesDigital > AnimesFire)
- ✅ Tratamento de falha em fonte fallback
- ✅ Homepage incremental search para AnimesDigital
- ✅ Suporte a episodes descobertos dinamicamente

**🐛 Correções**
- ✅ Fallback source now validates non-empty chapters
- ✅ AnimesDigital ?odr=1 parameter requirement documented
- ✅ Episode order sorting and deduplication
- ✅ Homepage search matching precision

### v0.2.0 (Dezembro 2025) - Refactor & Performance

**🔄 Trocar Fonte Durante Reprodução**
- ✅ Opção "🔄 Trocar fonte" no menu pós-episódio
- ✅ Alterna entre versões dublada/legendada/diferentes scrapers
- ✅ Útil quando a fonte atual não tem episódios mais recentes
- ✅ Mostra todas as variações encontradas para o anime base
- ✅ Disponível em busca normal e fluxo AniList

**🎵 Refatoração Manga CLI**
- ✅ Mangá refatorado para seguir MVCP (Model-View-Controller-Plugin)
- ✅ Service layer MangaDex com erro handling e cache
- ✅ Substituição de `input()` por Rich + InquirerPy menus
- ✅ Spinners de loading para API calls
- ✅ Histórico de leitura em JSON (`manga_history.json`)
- ✅ Resume hint "⮕ Retomar" mostra último capítulo lido
- ✅ Configuração centralizada com Pydantic (`config.py`)
- ✅ Pydantic data models para MangaMetadata, ChapterData, etc
- ✅ Cache de capítulos (24h padrão, configurável)
- ✅ Múltiplos idiomas (pt-br, en, ja padrão)

**⚡ Performance e Cache**
- ✅ Cache de episódios: carrega instantaneamente lista de episódios já visitados
- ✅ Cache de scrapers: resultados de busca salvos para acesso rápido
- ✅ Correção de crash ao usar cache de episódios
- ✅ Migração de Textual para Rich + InquirerPy (TUI 65% menor, 10x mais rápido)

**🎉 Melhorias AniList**
- ✅ Adição automática de anime à lista Watching ao começar a assistir
- ✅ Menu de conta AniList: veja perfil e estatísticas no terminal
- ✅ Melhoria na navegação: ESC para voltar, Q para sair
- ✅ Correção de FileNotFoundError ao executar CLI de fora da pasta do projeto

**🔧 Qualidade de Código**
- ✅ Aplicação completa de linting Ruff
- ✅ Melhorias de formatação e mensagens
- ✅ Adição de OpenSpec para documentação de mudanças

### v0.2.0 (Integração AniList Completa)

**🎉 Integração AniList**
- ✅ Autenticação OAuth com AniList.co
- ✅ Navegação por listas (Watching, Planning, Completed, etc)
- ✅ Visualização de trending anime
- ✅ Sincronização automática de progresso após assistir episódios
- ✅ Confirmação "assistiu até o final" antes de atualizar
- ✅ Mapeamento inteligente: salva título correto do scraper para cada anime
- ✅ Retoma automaticamente no episódio correto (AniList + histórico local)
- ✅ Busca flexível: tenta romaji primeiro, depois inglês
- ✅ Suporte a títulos bilíngues (romaji + inglês)

**🔧 Melhorias de UX**
- ✅ Menu de opções quando há progresso salvo (continuar ou escolher episódio)
- ✅ Navegação com ESC para voltar nos menus
- ✅ Indicadores visuais de progresso (episódio X/Y, rating)

### v0.1.0 (Base)
- ✅ Sistema de plugins para múltiplos scrapers
- ✅ Integração com mpv para reprodução
- ✅ Menu curses em português brasileiro
- ✅ Histórico local de episódios assistidos
- ✅ Suporte a modo debug
- ✅ Instalação via UV tool

---

🎬 **Bom anime!**
