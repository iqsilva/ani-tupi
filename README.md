# 🎬 ani-tupi

Assista anime sem anúncios! API + interface web (PWA) em português brasileiro.

[![PyPI](https://img.shields.io/pypi/v/ani-tupi)](https://pypi.org/project/ani-tupi/)
[![Python](https://img.shields.io/pypi/pyversions/ani-tupi)](https://pypi.org/project/ani-tupi/)

> Estava cansado de anúncios e o ani-cli não tinha conteúdo em português brasileiro, então criei esta ferramenta.

## 📋 Requisitos

- **Python 3.12+** (obrigatório)
- **mpv** (player de vídeo)
- **Browsers do Scrapling** (opcional — necessário apenas para as fontes anroll/animesdigital; instale com `just scrapling-install`. Indisponível em ARM/Raspberry Pi: as demais fontes funcionam normalmente)

### Instalando dependências

#### Linux (Arch)
```bash
sudo pacman -S python mpv chromium
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt install python3 mpv chromium-browser
```

#### Linux (Fedora)
```bash
sudo dnf install python3 mpv chromium
```

#### macOS
```bash
brew install python@3.12 mpv chromium
```

#### Windows
Recomendamos usar [Chocolatey](https://chocolatey.org/install):
```powershell
# Como administrador
choco install python mpv googlechrome
```

## 🚀 Instalação

### Via [PyPI](https://pypi.org/project/ani-tupi/) (Recomendado)

Você ainda precisa das [dependências de sistema](#-requisitos) (`mpv`, etc.) — elas não vêm com o pacote PyPI.

```bash
# Recomendado: instala ani-tupi como ferramenta global
uv tool install ani-tupi

# Alternativa: pip (dentro de um venv)
pip install ani-tupi
```

Atualizar para a versão mais recente:

```bash
uv tool install --upgrade ani-tupi
```

## ⚡ Uso

Inicie o servidor:

```bash
ani-tupi
```

Depois acesse a interface web em `http://localhost:8000` (a porta padrão pode ser alterada nas configurações).

- 📱 A interface é uma PWA — pode ser instalada no celular/desktop
- 📖 Documentação da API: `http://localhost:8000/api/docs`

### Principais recursos

- 🔍 **Busca** em múltiplas fontes brasileiras simultaneamente
- ▶️ **Reprodução via mpv** controlada pela interface web (play/pause, seek, próximo episódio)
- 🕘 **Histórico** — continue de onde parou
- ⚙️ **Fontes configuráveis** — priorize ou desative fontes pela interface

### Configuração

Configurações são carregadas nesta ordem de precedência:

1. Variáveis de ambiente (`ANI_TUPI__...`)
2. Overrides salvos pelo usuário (`~/.config/ani-tupi/settings.json`)
3. Valores padrão da aplicação

Exemplo:

```bash
export ANI_TUPI__API__PORT=8080
```

## 🔧 Para Desenvolvedores

### Modo desenvolvimento

```bash
# Instalar dependências
uv sync

# Rodar o servidor
just serve
# ou: uv run uvicorn api.server:app --host 0.0.0.0 --port 8000

# Rodar testes
just test

# Lint / formatação
just lint
just format
```

### Comandos úteis (justfile)

| Comando | Descrição |
|---------|-----------|
| `just serve` | Inicia o servidor da API |
| `just test` | Roda a suíte de testes |
| `just clear-cache` | Limpa cache de busca e episódios |
| `just clear-history` | Limpa histórico de reprodução |
| `just clear-all` | Limpa tudo (cache + histórico) |

### Publicação PyPI (mantenedores)

Secrets necessários no repositório GitHub:

| Secret | Uso |
|--------|-----|
| `TESTPYPI_API_TOKEN` | Upload para [TestPyPI](https://test.pypi.org) |
| `PYPI_API_TOKEN` | Upload para PyPI oficial (após validação) |

Variável de repositório:

| Variável | Valor | Efeito |
|----------|-------|--------|
| `PYPI_PUBLISH_ENABLED` | `true` | Habilita upload para PyPI no workflow de release |

### Por que UV?

[UV](https://github.com/astral-sh/uv) é um gerenciador de pacotes Python extremamente rápido:
- ⚡ 10-100x mais rápido que pip
- 🔒 Lock file determinístico (`uv.lock`)
- 📦 Gerenciamento de venv automático
- 🌍 Multiplataforma (Linux, macOS, Windows)

## 🐛 Problemas Conhecidos

### MPV não abre
Verifique se o mpv está instalado:
```bash
mpv --version
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma issue ou pull request.

> 📖 **Antes de mexer no código, leia [`CONTRIBUTING.md`](./CONTRIBUTING.md)** —
> especialmente a seção **Filosofia de fontes**, que explica as decisões do autor
> sobre priorização de fontes (velocidade, qualidade HD e legenda) e as regras
> que todo PR deve preservar.

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
- Arquitetura de aplicações em Python
- Web scraping e parsing de HTML
- APIs REST/WebSocket com FastAPI
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
- ✅ **Aprendizado**: Estude como construir web scrapers e APIs
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
- [Eduardo Nery](https://github.com/eduardonery1) — autor do projeto original [ani-tupi](https://github.com/eduardonery1/ani-tupi), do qual este fork é derivado
