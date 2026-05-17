# 10. Implantação (Deploy)

## 10.1 Visão Geral da Infraestrutura

Sendo um projeto acadêmico, a arquitetura de implantação foi simplificada para utilizar serviços gratuitos (Free Tier) em modelo PaaS (Platform as a Service), eliminando a necessidade de gerenciar servidores complexos, Docker ou Redis.

* **Backend / API:** [Render](https://render.com/) (Web Service)
* **Banco de Dados:** [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (Tier M0 - Gratuito)
* **Armazenamento de Imagens:**  AWS S3

---

## 10.2 MongoDB Atlas

### Configuração (Free Tier)

| Parâmetro | Configuração |
|---|---|
| **Tier** | M0 (Free) |
| **Região** | sa-east-1 (São Paulo) ou us-east-1 |
| **Replica Set** | 3 nós (padrão do Atlas) |
| **Storage** | 512MB (suficiente para projeto acadêmico) |
| **Network** | Permitir acesso de qualquer IP (`0.0.0.0/0`) para o Render conectar |

### Setup Inicial

```bash
# 1. Criar conta no MongoDB Atlas e iniciar um cluster M0 (Free)
# 2. Em "Database Access", criar um usuário e senha (ex: admin / admin123)
# 3. Em "Network Access", adicionar IP "0.0.0.0/0"
# 4. Obter a connection string em "Connect" -> "Connect your application"

# Formato da connection string:
MONGODB_URI="mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/cardapio_online?retryWrites=true&w=majority"
```

---

## 10.3 Deploy no Render

O Render permite implantação direta a partir do repositório no GitHub, sem necessidade de Docker.

### 1. Preparação do Projeto

No arquivo `settings.py` (ou `production.py`), garanta que o Django Channels utilize o *InMemoryChannelLayer* (já que não teremos Redis nesta arquitetura simplificada):

```python
# app/settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```

Crie na raiz do projeto um script `build.sh` (e lembre-se de dar permissão com `chmod +x build.sh` se estiver no Linux/Mac):
```bash
#!/usr/bin/env bash
# build.sh
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
```

### 2. Configuração no Dashboard do Render

1. Crie uma conta no Render e adicione um novo **Web Service**.
2. Conecte com o repositório do projeto no GitHub.
3. Preencha as configurações:
   - **Environment:** `Python 3`
   - **Build Command:** `./build.sh`
   - **Start Command:** `daphne -b 0.0.0.0 -p $PORT app.asgi:application` (Daphne gerencia requisições HTTP e WebSocket).

### 3. Variáveis de Ambiente (Environment Variables)

No dashboard do Render, adicione as seguintes variáveis de ambiente:

```env
PYTHON_VERSION=3.12.0
DJANGO_SECRET_KEY=sua-chave-super-secreta
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*
MONGODB_URI=mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/cardapio_online
```

---

## 10.4 CI/CD Pipeline

O CI/CD é gerenciado nativamente pelo Render, simplificando o processo:
1. Você faz um `git push` para a branch principal (`main` ou `master`).
2. O Render detecta o commit no GitHub via webhook de forma automática.
3. O Render executa o comando de build (`./build.sh`).
4. Se o build for bem-sucedido, o novo código vai ao ar.

---

## 10.5 Checklist de Deploy

### Pré-Deploy
- [ ] Cluster MongoDB Atlas M0 criado e connection string obtida.
- [ ] IP `0.0.0.0/0` liberado na aba Network do Atlas.
- [ ] Script `build.sh` criado na raiz do repositório.
- [ ] `InMemoryChannelLayer` configurado para o WebSocket funcionar sem Redis.
- [ ] Código atualizado na branch principal do GitHub.

### Deploy
- [ ] Web Service criado no painel do Render.
- [ ] Variáveis de ambiente configuradas no Render.
- [ ] Deploy concluído (status `Live` no dashboard).

### Pós-Deploy
- [ ] Acessar URL fornecida (ex: `https://cardapio-online.onrender.com`).
- [ ] Testar cadastro e login de usuário.
- [ ] Testar fluxo de pedido para validar o WebSocket.

---

## 10.6 Estimativa de Custos

| Serviço | Utilização | Custo Estimado |
|---|---|---|
| MongoDB Atlas | Cluster M0 (512MB) | **$0/mês** |
| Render | Free Tier (Web Service 512MB RAM) | **$0/mês** |
| AWS S3 / Cloudinary | Plano gratuito | **$0/mês** |
| **Total** | | **$0/mês** |

