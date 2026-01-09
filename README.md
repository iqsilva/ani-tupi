# 🎬 ani-tupi

Assista anime direto do terminal sem anúncios! Interface CLI em português brasileiro.

> Estava cansado de anúncios e o ani-cli não tinha conteúdo em português brasileiro, então criei esta ferramenta.

## 📺 Demo no YouTube
[![Demo](https://img.youtube.com/vi/eug6gKLTD3I/maxresdefault.jpg)](https://youtu.be/eug6gKLTD3I)

## ⭐ Integração com AniList (Recomendado!)

**Sincronize automaticamente seu progresso com [AniList.co](https://anilist.co)!**

ani-tupi agora possui integração completa com AniList, permitindo:

- 📈 **Trending** - Descubra os animes mais populares do momento
- 📅 **Recentes** - Continue de onde parou (histórico local)
- 📺 **Watching** - Acesse sua lista "Assistindo" do AniList
- 📋 **Planning** - Veja animes que você planeja assistir
- ✅ **Completed** - Histórico de animes completos
- 🔄 **Sincronização automática** - Progresso atualiza no AniList após cada episódio
- 📝 **Adição automática à Watching** - Adiciona anime à sua lista ao começar a assistir
- 💾 **Mapeamento inteligente** - Lembra do título correto do scraper para cada anime
- ⚡ **Cache de episódios** - Carrega lista de episódios instantaneamente na segunda vez
- 🚀 **Cache de scrapers** - Resultados de busca salvos para acesso rápido
- ✅ **Confirmação de progresso** - Pergunta se assistiu até o final antes de atualizar
- 👤 **Menu de conta AniList** - Veja seu perfil e estatísticas
- 🎯 **Títulos bilíngues** - Veja nomes em romaji + inglês
- ⌨️ **Navegação rápida** - Use ESC para voltar, setas para navegar

**Setup rápido (30 segundos):**

```bash
# 1. Fazer login (apenas uma vez)
ani-tupi anilist auth

# 2. Navegar suas listas + trending
ani-tupi anilist

# 3. Assista normalmente - tudo sincroniza automaticamente! ✨
```

Mesmo método usado por [viu-media](https://github.com/viu-media/viu) - simples e confiável!

---

## 📋 Requisitos

- **Python 3.12+** (obrigatório)
- **mpv** (player de vídeo)
- **Firefox** (para scraping)
- **geckodriver** (driver para Selenium + Firefox)
- **git** (para clonar o repositório)

### Instalando dependências

#### Linux (Arch)
```bash
sudo pacman -S python mpv firefox geckodriver git
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt install python3 mpv firefox git
# Instale geckodriver separadamente ou compile:
# https://github.com/mozilla/geckodriver/releases
```

#### Linux (Fedora)
```bash
sudo dnf install python3 mpv firefox git geckodriver
```

#### macOS
```bash
brew install python@3.12 mpv firefox git geckodriver
```

#### Windows
Recomendamos usar [Chocolatey](https://chocolatey.org/install):
```powershell
# Como administrador
choco install python mpv firefox git geckodriver
```

## 🚀 Instalação

### Instalação CLI Global (Recomendado)

Instala `ani-tupi` e `manga-tupi` como comandos globais - use em qualquer lugar do sistema!

**Requisito:** Apenas Python 3.12+ (UV é instalado automaticamente pelo script)

```bash
# Clone o repositório
git clone https://github.com/levyvix/ani-tupi
cd ani-tupi

# Execute o instalador
python3 install-cli.py
```

**O instalador faz automaticamente:**
- ✅ Instala UV se não estiver presente
- ✅ Instala ani-tupi como ferramenta global usando UV
- ✅ Configura comandos `ani-tupi` e `manga-tupi`
- ✅ Mostra instruções para adicionar ao PATH se necessário

**Depois de instalado, use:**
```bash
ani-tupi                      # Buscar e assistir anime
ani-tupi --continue-watching  # Continuar último anime
ani-tupi anilist auth         # Autenticar com AniList.co
ani-tupi anilist              # Navegar suas listas no AniList
manga-tupi                    # Ler mangá
```

### Instalação Manual

Se preferir instalar manualmente com UV:

```bash
# 1. Instale UV (se não tiver)
curl -LsSf https://astral.sh/uv/install.sh | sh         # Linux/macOS
# ou: irm https://astral.sh/uv/install.ps1 | iex        # Windows PowerShell

# 2. Clone e instale
git clone https://github.com/levyvix/ani-tupi
cd ani-tupi
uv tool install .
```

### Modo Desenvolvimento

Para desenvolvedores - roda sem instalar globalmente:

```bash
git clone https://github.com/levyvix/ani-tupi
cd ani-tupi
uv sync                # Instala dependências
uv run ani-tupi        # Executa sem instalar
uv run main.py --debug # Modo debug
```

## 💻 Como Usar

### Comandos Básicos

Após instalação global:

```bash
# Assistir anime
ani-tupi

# Continuar assistindo último anime
ani-tupi --continue-watching
ani-tupi -c

# Buscar anime específico
ani-tupi --query "dandadan"
ani-tupi -q "dandadan"

# AniList - Sincronizar com AniList.co
ani-tupi anilist auth      # Fazer login (apenas uma vez)
ani-tupi anilist           # Navegar listas e trending

# Ler mangá
manga-tupi

# Ver ajuda
ani-tupi --help
```

**AniList Integration:**
- `ani-tupi anilist auth` - Autentica com AniList.co (necessário apenas uma vez)
- `ani-tupi anilist` - Navega trending, watching, planning, completed e outras listas
- Sincronização automática - Seu progresso atualiza automaticamente após assistir cada episódio

### Atalhos Durante Reprodução (MPV)

Durante a reprodução de episódios, você pode usar estes atalhos para navegação rápida:

| Atalho | Ação | Efeito | Feedback no Terminal |
|--------|------|--------|---------------------|
| `Shift+N` | Próximo | Marca como assistido e carrega próximo episódio | `▶️  Reproduzindo Episódio {N}` |
| `Shift+P` | Anterior | Volta para o episódio anterior | `⏪ Voltando para Episódio {N}` |
| `Shift+M` | Marcar e Menu | Marca como assistido e volta ao menu | `📋 Episódio {N} marcado - Retornando ao menu` |
| `Shift+R` | Recarregar | Recarrega o episódio atual | `🔄 Recarregando Episódio {N}` |
| `Shift+A` | Auto-play | Alterna auto-play: ao sair (q) vai para próximo episódio automaticamente | `🔄 Auto-play ATIVADO/DESATIVADO` |
| `Shift+T` | Trocar Áudio | Alterna entre legendado/dublado (se disponível) | `🔄 Alternando legendado/dublado (se disponível)` |

**Notas:**
- Todos os atalhos exibem feedback tanto no terminal quanto na tela do MPV (OSD)
- O progresso é salvo automaticamente no histórico local e sincronizado com AniList (se autenticado)
- **Auto-play (Shift+A):**
  - Alterna modo global para toda a sessão (funciona mesmo trocando de anime)
  - Por padrão: **desativado** ao iniciar o app
  - Quando **ativado**: ao sair do player com `q`, marca episódio como assistido e carrega próximo automaticamente
  - Quando **desativado**: ao sair com `q`, volta ao menu normalmente
- Use `q` para sair do player (com auto-play ativado, avança automaticamente; desativado, volta ao menu)

### Ler Mangá

Leia mangá do MangaDex direto do terminal!

```bash
# Ler mangá interativamente
manga-tupi
```

**Features:**
- 🔍 **Busca em tempo real**: Digite para procurar manga
- 📖 **Menu interativo**: Selecione com setas, ESC para voltar
- 💾 **Histórico de leitura**: Salva o último capítulo lido
- ⮕ **Retomar leitura**: Hint "⮕ Retomar" mostra o último capítulo
- 🖼️ **Visualizador de imagens**: Abre automaticamente no seu viewer padrão (feh, Preview, etc)
- 🔄 **Cache de capítulos**: Carrega lista de capítulos instantaneamente
- ⚙️ **Configurável**: Customize pasta de download, idiomas preferidos, etc
- ⏳ **Loading spinners**: Feedback visual durante API calls

**Configuração (opcional):**

```bash
# Pasta de download padrão é ~/Downloads
# Para customizar, use variáveis de ambiente:

export ANI_TUPI__MANGA__OUTPUT_DIRECTORY=~/Mangas
export ANI_TUPI__MANGA__CACHE_DURATION_HOURS=48
export ANI_TUPI__MANGA__LANGUAGES=pt-br,en,ja
```

### Integração AniList

Sincronize seu progresso com [AniList.co](https://anilist.co) automaticamente!

```bash
# Fazer login no AniList
ani-tupi anilist auth

# Navegar listas do AniList
ani-tupi anilist

# Ou apenas (menu é o padrão)
ani-tupi anilist menu
```

**Features:**
- 📈 **Trending**: Veja os animes mais populares do momento
- 📺 **Watching**: Continue de onde parou (se logado)
- 📋 **Planning**: Animes que você planeja assistir
- ✅ **Completed**: Histórico de animes completos
- ⏸️ **Paused** / ❌ **Dropped** / 🔁 **Rewatching**: Todas as suas listas
- 🔄 **Sincronização automática**: Progresso atualiza no AniList após assistir cada episódio
- 📝 **Adição automática à lista Watching**: Adiciona anime à sua lista ao começar a assistir
- 💾 **Mapeamento inteligente**: Salva o título correto do scraper para cada anime do AniList
- ⚡ **Cache de episódios**: Carrega lista de episódios instantaneamente na segunda vez
- 🚀 **Cache de scrapers**: Resultados de busca salvos para acesso rápido
- ✅ **Confirmação de progresso**: Pergunta se você assistiu até o final antes de sincronizar
- 👤 **Menu de conta AniList**: Veja seu perfil e estatísticas diretamente no terminal
- 🎯 **Continuar de onde parou**: Retoma automaticamente no episódio certo (AniList + histórico local)
- 🔍 **Busca flexível**: Tenta romaji primeiro, depois inglês se não encontrar
- 📝 **Múltiplas fontes**: Se encontrar múltiplos resultados, deixa você escolher o correto
- 🔄 **Trocar fonte durante reprodução**: Mude entre versões dublada/legendada/diferentes scrapers após assistir um episódio quando a fonte atual não tiver novos episódios disponíveis

**Como funciona:**
1. Faça login uma vez com `ani-tupi anilist auth`
2. Use `ani-tupi anilist` para navegar suas listas
3. Selecione um anime → ani-tupi busca nos scrapers
4. Assista normalmente → progresso sincroniza automaticamente!

### Modo Desenvolvimento

Se está desenvolvendo (sem instalação global):

```bash
uv run ani-tupi              # Executar
uv run main.py --debug       # Com debug
uv run main.py -q "naruto"   # Buscar direto
```

### Build para Distribuição

Para criar executável standalone (não precisa Python instalado):

```bash
uv run build.py
```

O executável será criado em `dist/ani-tupi` (Linux/macOS) ou `dist/ani-tupi.exe` (Windows), junto com a pasta `plugins/`.

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
├── build.py             # Build executável standalone
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

# Buildar executável standalone
uv run build.py

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

## 📦 Usando Release Pré-compilada

Se houver uma release disponível, você pode baixar o executável direto:

```bash
# Baixe a release do GitHub
# Dê permissão de execução (Linux/macOS)
chmod +x ./ani-tupi

# Execute
./ani-tupi
```

## 🐛 Problemas Conhecidos

### Vídeo não abre (mostra "Buscando vídeo..." e pula para menu)

**Causa:** Geckodriver não está instalado ou não está no PATH.

**Solução:**

**Arch:**
```bash
sudo pacman -S geckodriver
```

**Ubuntu/Debian:**
```bash
# Método 1: Via repositório (se disponível)
sudo apt install firefox-geckodriver
# Ou compile manualmente:
wget https://github.com/mozilla/geckodriver/releases/download/v0.33.3/geckodriver-v0.33.3-linux64.tar.gz
tar -xvf geckodriver-v0.33.3-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
sudo chmod +x /usr/local/bin/geckodriver
```

**Verificar instalação:**
```bash
geckodriver --version
which geckodriver
```

### "FileNotFoundError" ao salvar histórico
Corrigido na versão 0.1.0+. Atualize para a versão mais recente.

### MPV não abre
Verifique se o mpv está instalado:
```bash
mpv --version
```

### Firefox não encontrado
Certifique-se de que o Firefox está no PATH do sistema.

**Verificar:**
```bash
which firefox
firefox --version
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

## 📝 Changelog

### Versão Atual (Dezembro 2025)

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
- ✅ Build com PyInstaller
- ✅ Instalação via UV tool

---

🎬 **Bom anime!**
