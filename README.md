# oidc-auth-sentry

Provedor de SSO via **OpenID Connect** para o **Sentry self-hosted**, adaptado
do provedor Google nativo do Sentry. Testado com **AWS Cognito User Pools**, mas
funciona com qualquer IdP compatível com OIDC (os endpoints são configuráveis,
não fixos no código).

- Nome de distribuição (pip): `oidc-auth-sentry`
- Módulo importável: `oidc`
- Compatível com Sentry self-hosted (registro automático via entry point `sentry.apps`)

## Como funciona

O Sentry descobre apps instalados pelo entry point `sentry.apps`. Ao iniciar,
ele chama `oidc.apps.Config.ready()`, que registra o `OIDCProvider` no registro
de autenticação do Sentry. **Não é preciso editar o código-fonte do Sentry.**

Assim como o provedor Google, o `id_token` (JWT) devolvido pelo endpoint de
token é decodificado diretamente — sem chamada extra ao `userinfo`. Os claims
`iss` (issuer) e `aud` (audience) são validados. A assinatura do JWT
**não** é verificada, pois o token é obtido por TLS direto do endpoint de token
no passo anterior (mesmo comportamento do provedor Google). Para verificação de
assinatura via JWKS, veja o comentário em `oidc/views.py`.

---

## Passo a passo

### 1. Criar o App Client no Cognito

1. No console da AWS, abra **Amazon Cognito → User Pools** e selecione seu pool.
2. Em **App clients**, crie (ou edite) um app client **com client secret**.
3. Em **Hosted UI / Managed login**, configure:
   - **Allowed callback URLs**: `https://SEU-SENTRY/auth/sso/`
     (substitua `SEU-SENTRY` pelo seu `url-prefix`; a barra final é obrigatória)
   - **OAuth grant types**: `Authorization code grant`
   - **OpenID Connect scopes**: `openid`, `email`, `profile`
4. Garanta que o pool tem um **domínio** configurado (Hosted UI), algo como
   `https://SEU-DOMINIO.auth.SUA-REGIAO.amazoncognito.com`.
5. Anote: **client id**, **client secret**, o **domínio** do Hosted UI, a
   **região** e o **User Pool ID**.

Os valores que você vai usar:

| Dado            | Onde encontrar                              | Exemplo                                                        |
| --------------- | ------------------------------------------- | -------------------------------------------------------------- |
| `client-id`     | App client                                  | `7exampleabc123`                                               |
| `client-secret` | App client                                  | `abcd...`                                                      |
| `authorize-url` | Domínio Hosted UI + `/oauth2/authorize`     | `https://id.example.com/oauth2/authorize`                      |
| `token-url`     | Domínio Hosted UI + `/oauth2/token`         | `https://id.example.com/oauth2/token`                          |
| `issuer`        | `cognito-idp.<regiao>.amazonaws.com/<pool>` | `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123` |

> Dica: confira o discovery em
> `https://cognito-idp.<regiao>.amazonaws.com/<pool>/.well-known/openid-configuration`
> — os campos `authorization_endpoint`, `token_endpoint` e `issuer` confirmam os
> valores acima.

### 2. Instalar o plugin no Sentry self-hosted

No seu checkout do `getsentry/self-hosted`, adicione o pacote em
`sentry/requirements.txt`:

```
oidc-auth-sentry==0.2.0
```

Se o pacote estiver num índice privado (ex.: AWS CodeArtifact), exporte as
variáveis de índice antes do build:

```
PIP_INDEX_URL=https://SEU-INDICE/simple/
PIP_EXTRA_INDEX_URL=https://pypi.org/simple/
```

Em seguida rode o instalador, que reconstrói e reinicia os containers:

```
./install.sh
```

### 3. Configurar as opções do Sentry

Adicione as cinco opções `auth-oidc.*`. Há duas formas equivalentes.

**Opção A — `sentry/config.yml`:**

```yaml
auth-oidc.client-id: "7exampleabc123"
auth-oidc.client-secret: "SEU_CLIENT_SECRET"
auth-oidc.authorize-url: "https://id.example.com/oauth2/authorize"
auth-oidc.token-url: "https://id.example.com/oauth2/token"
auth-oidc.issuer: "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123"
```

Depois de editar arquivos de configuração, rode `./install.sh` novamente para
aplicar.

**Opção B — via CLI (sem rebuild):**

```bash
docker compose run --rm web sentry config set auth-oidc.client-id "7exampleabc123"
docker compose run --rm web sentry config set auth-oidc.client-secret "SEU_CLIENT_SECRET"
docker compose run --rm web sentry config set auth-oidc.authorize-url "https://id.example.com/oauth2/authorize"
docker compose run --rm web sentry config set auth-oidc.token-url "https://id.example.com/oauth2/token"
docker compose run --rm web sentry config set auth-oidc.issuer "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123"
```

#### Opcional — claims do nome de exibição

O nome de exibição do usuário é resolvido a partir de uma lista ordenada de
claims do `id_token` — o primeiro presente e não-vazio vence, com o `email`
como fallback final. O padrão segue os claims OIDC padrão:

```
name,preferred_username,email
```

Se o seu IdP usa um claim não-padrão, defina `auth-oidc.name-claims` (lista
separada por vírgula). Por exemplo, o AWS Cognito emite `cognito:username` em
vez do `preferred_username` padrão:

```bash
docker compose run --rm web sentry config set auth-oidc.name-claims "name,cognito:username,email"
```

#### Opcional — nome do provedor (rebrand)

O rótulo exibido na UI de SSO é `OIDC` por padrão. Para personalizar (ex.:
`Custom SSO`), defina `auth-oidc.provider-name`:

```bash
docker compose run --rm web sentry config set auth-oidc.provider-name "Custom SSO"
```

> O nome é resolvido no boot do container; após alterar, reinicie/reaplique
> para que a UI mostre o novo rótulo.

#### Opcional — restrição por domínio de email

Por padrão **qualquer domínio é aceito**. Para permitir apenas domínios
específicos, defina `auth-oidc.allowed-domains` (lista separada por vírgula). O
domínio é extraído do email do `id_token` (a parte após o `@`); quem não bater
é recusado no login:

```bash
docker compose run --rm web sentry config set auth-oidc.allowed-domains "example.com,example.org"
```

#### Opcional — restrição por grupos

Por padrão **qualquer grupo (ou nenhum) é aceito**. Para limitar o acesso a
membros de grupos específicos, defina duas opções:

- `auth-oidc.groups-claim` — o claim do `id_token` que carrega os grupos.
  Padrão: `groups` (claim OIDC padrão). No AWS Cognito é `cognito:groups`.
- `auth-oidc.allowed-groups` — lista separada por vírgula de grupos liberados.
  O usuário precisa pertencer a **pelo menos um** deles.

```bash
docker compose run --rm web sentry config set auth-oidc.groups-claim "cognito:groups"
docker compose run --rm web sentry config set auth-oidc.allowed-groups "sentry-admins,sentry-users"
```

> O IdP precisa incluir os grupos no `id_token`. O Cognito injeta
> `cognito:groups` automaticamente para usuários que pertencem a algum grupo do
> User Pool. Se `auth-oidc.allowed-groups` ficar vazio, nenhuma checagem de
> grupo é feita.

### 4. Habilitar o SSO na organização

1. Faça login no Sentry como **owner** da organização.
2. Vá em **Settings → Auth** (Settings da organização).
3. O provedor **OIDC** deve aparecer na lista. Clique para configurar.
4. Conclua o fluxo de login com uma conta do seu User Pool para vincular o SSO.
5. Opcionalmente, **exija SSO** para toda a organização.

> Atenção: ao exigir SSO, esse passa a ser o único meio de login na sua
> instância. Garanta que pelo menos uma conta owner consegue autenticar pelo
> Cognito antes de tornar obrigatório.

### 5. Verificar

- Acesse `https://SEU-SENTRY/auth/login/` e inicie o login pelo provedor OIDC.
- Você será redirecionado ao Hosted UI do Cognito, autentica, e volta logado.
- Se algo falhar, veja os logs do container `web`:
  `docker compose logs -f web | grep sentry.auth.oidc`

---

## Mapeamento de identidade

O provedor lê os seguintes claims do `id_token`:

| Claim                                 | Uso no Sentry                                                |
| ------------------------------------- | ------------------------------------------------------------ |
| `sub`                                 | id estável e único do usuário                                |
| `email`                               | e-mail (e id legado, para casar contas já existentes)        |
| `name` → `cognito:username` → `email` | nome de exibição (nessa ordem de fallback)                   |
| `email_verified`                      | repassado ao Sentry                                          |
| `iss`, `aud`                          | validados (devem casar com `auth-oidc.issuer` e o client id) |

### Restrição opcional por domínio de e-mail

Diferente do provedor Google, não usamos o claim `hd`. Se quiser limitar o
acesso a um domínio, isso é derivado do e-mail. (Configurável no provider;
por padrão nenhum domínio é exigido.)

---

## Solução de problemas

| Sintoma                                 | Causa provável                                                                                       |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `redirect_uri mismatch` no Cognito      | A callback URL no app client precisa ser exatamente `https://SEU-SENTRY/auth/sso/` (com barra final) |
| `id_token issuer mismatch`              | `auth-oidc.issuer` não bate com o `iss` do token — confira região e User Pool ID                     |
| `id_token audience mismatch`            | `auth-oidc.client-id` diferente do app client que gerou o token                                      |
| Provedor não aparece em Settings → Auth | Pacote não instalado / `./install.sh` não rodou após adicionar ao requirements                       |
| `Unable to fetch user information`      | Faltou o scope `openid`/`email`, ou o app client não permite o grant `authorization_code`            |

---

## Desenvolvimento

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest -q
```

Build local e validação do pacote:

```bash
python -m build
python -m twine check dist/*
```

## Release

A versão fica em `pyproject.toml`. Para publicar a `0.2.0`:

```bash
git tag v0.2.0
git push origin v0.2.0
```

A tag dispara o workflow `release.yml`, que valida que a tag bate com a versão,
builda e publica no índice configurado (PyPI via trusted publishing, ou um
índice privado). Veja `.github/workflows/release.yml`.
