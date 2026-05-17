# 10. Implantação e Operação de Infraestrutura (Deploy)

Este documento centraliza as diretrizes, pré-requisitos e processos de entrega da plataforma para ambientes em nuvem, baseados em uma arquitetura de Plataforma como Serviço (PaaS).

---

## Sumário

- [10.1 Visão Geral da Arquitetura Focada em Nuvem](#101-visão-geral-da-arquitetura-focada-em-nuvem)
- [10.2 Configuração de Banco e Storage Remoto](#102-configuração-de-banco-e-storage-remoto)
- [10.3 Provisionamento da Aplicação e Servidor Web](#103-provisionamento-da-aplicação-e-servidor-web)
- [10.4 Fluxo de Integração e Entrega Contínua (CI/CD)](#104-fluxo-de-integração-e-entrega-contínua-cicd)
- [10.5 Procedimentos de Checklist Operacional](#105-procedimentos-de-checklist-operacional)
- [10.6 Previsão Financeira e Limites de Serviço](#106-previsão-financeira-e-limites-de-serviço)

---

## 10.1 Visão Geral da Arquitetura Focada em Nuvem

Considerando eficiência financeira para lançamento do SaaS e validação em menor escala, a estratégia dispensa o uso complexo de provedores elásticos crus (IaaS, Kubernetes ou EC2) em favor do gerenciamento através do Render (PaaS), permitindo resiliência base com escalabilidade facilitada e manutenções passivas de containers sem servidor local de Redis.

* **Processamento / API Node:** [Render Web Service](https://render.com/) — Serviço escalável suportando tráfego HTTP e WebSocket dinâmicos.
* **Cluster de Dados Persistente:** [MongoDB Atlas](https://www.mongodb.com/) — Gerenciado pela própria AWS/Google sob abstração NoSQL em formato Replica Set para tolerância à queda.
* **Infraestrutura de Assets Fotográficos:** Integração via APIs com a Amazon S3 ou serviços passivos como o Cloudinary para mitigar *Bandwidth Load* proveniente das fotos dos estabelecimentos.

---

## 10.2 Configuração de Banco e Storage Remoto

O banco primário operará através das definições globais providas pelo modelo do MongoDB Atlas.

### Configuração Regulatória de DB (Atlas)

| Critério Arquitetural | Ajuste Configurado |
| --- | --- |
| **Padrão Distribuído** | Cluster distribuído nativamente (Replica Set primário com 3 nós ativos focados). |
| **Zona de Operação** | Infraestrutura provisionada na `sa-east-1` (América Latina/São Paulo) ou `us-east-1` focando baixa latência. |
| **Regras de Parede (Network)** | Whitelist aberta `0.0.0.0/0` para autorizar exclusivamente a interconexão com as malhas dinâmicas rotativas de IP da rede Render. |
| **String de Interconexão SRV** | Assinatura padrão: `mongodb+srv://<auth_user>:<auth_pass>@clusterX.XXXX.mongodb.net/` |

---

## 10.3 Provisionamento da Aplicação e Servidor Web

A implantação do ecossistema centraliza-se na compilação autônoma do servidor via script de *Build* interno vinculado aos hooks diretos do repositório remoto. 

### Diretrizes de Modificações no Ambiente Base

Para atuar na nuvem de forma leve e mitigar os custos em fase inicial, substitui-se o Layer do Channel Django por sua contraparte alocada integralmente em memória, eliminando a dependência atrelada ao servidor assíncrono isolado de Redis.

```python
# settings/production.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```

O contêiner virtual do Render executará em sequência obrigatória o preparo nativo exposto pelo arquivo utilitário da raiz do repositório:

```bash
#!/usr/bin/env bash
# build.sh

# Instrução de interrupção de esteira em caso de falha silenciosa:
set -o errexit

# Procedimentos de construção estrita:
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

### Parametrização Sensível (Environment Secrets)

Durante o processo de *Onboarding* da instância web, as seguintes travas de sistema (`ENV VARS`) devem ser cadastradas nos painéis avançados do provedor:

```env
PYTHON_VERSION=3.12.0
DJANGO_SECRET_KEY=[Hash de Entropia Longa Gerada Off-line]
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*
MONGODB_URI=[Connection String Oficial Originada pelo MongoDB Atlas]
AWS_ACCESS_KEY_ID=[Se habilitado e selecionado AWS S3]
AWS_SECRET_ACCESS_KEY=[Se habilitado e selecionado AWS S3]
```

O gatilho de execução pós-build obrigatório recai na invocação cruzada HTTP/WebSocket sustentada pelo ASGI Worker puro (*Daphne*):
> `daphne -b 0.0.0.0 -p $PORT app.asgi:application`

---

## 10.4 Fluxo de Integração e Entrega Contínua (CI/CD)

O motor do Render se alinha ao conceito GitOps garantindo lançamentos imutáveis isentos de interferência mecânica por administradores locais:
1.  **Versionamento e Fusão:** Aprovação de mudança técnica gerada no repositório matriz.
2.  **Sinalização Webhook:** O provedor da nuvem intercepta a mudança pela branch *Main* de modo automático.
3.  **Compilação em Caixa de Areia (Build Stage):** O servidor inicia a leitura do `build.sh`. Instala dependências em cascata isolada e formata blocos CSS/HTML estáticos minimizados.
4.  **Lançamento sem Queda (Blue-Green Routing):** Caso ocorra sucesso irrestrito nas fases de build, o tráfego entrante é migrado suavemente do worker anterior para a versão recentemente exposta e sadia, concretizando a entrega contínua.

---

## 10.5 Procedimentos de Checklist Operacional

Etapas restritivas que devem obrigatoriamente preceder qualquer *Go-Live* de produção para validação efetiva da integridade elástica do software e garantias contratuais de estabilidade.

### Revisão Arquitetural Estática (Pré-Deploy)
* [ ] Validação afirmativa de que `0.0.0.0/0` repousa sob os acessos aceitos na camada de DNS do Atlas Cloud.
* [ ] Conferencia sintática da credencial de autoridade contida na string URL do *MongoDB*.
* [ ] Confirmação afirmativa da existência e concessão das permissões de auto-execução sobre o utilitário `build.sh` armazenado.
* [ ] Verificação e acoplagem oficial da flag `InMemoryChannelLayer` na variável de contexto da instância voltada à produção para prevenir acidentes de *crash-loops* de WebSocket.

### Homologação Final Remota (Pós-Deploy)
* [ ] Obter HTTP Status 200 nas chamadas primárias do link HTTPS fornecido pela nuvem.
* [ ] Certificação do processo mecânico simulando um ciclo ponta-a-ponta (Cadastro de Restaurante, Cadastramento de Produtos).
* [ ] Auditoria de recepção do tráfego Bidirecional na simulação restrita do túnel de Pedidos (WebSocket real-time emitindo transições para telas não atualizadas).

---

## 10.6 Previsão Financeira e Limites de Serviço

Simulação técnica baseada no estágio e fase experimental (Tração Inicial).

| Entidade Alocada | Definição Paramétrica do Recurso Físico | Impacto de Custo de Execução (Mensal) |
| --- | --- | --- |
| **MongoDB Atlas** | Servidor Compartilhado (M0 Cloud 512 MB). | Totalmente Insento. |
| **Render Cloud Computing** | Fração Restrita de RAM e Instância de Processo em Standby (Sleep). | Totalmente Insento. |
| **Servidor de Blobs S3 / Cloudinary** | Faixa Base de Consumo Grátis de Tráfego Out-bound de Fotos. | Totalmente Insento. |
| **Somatória Geral do Projeto (TCO Inicial)** | Zero (Free Tier). | Total: R$ 0,00 |

*Aviso Técnico de Mitigação Sistêmica*: Modelos não remunerados submetem suas instâncias ao estado de suspensão ("Sleep state") após intervalos temporais médios de 15 minutos desprovidos de impulsos HTTP. O primeiro toque ("Cold Start") induzirá uma ignição demorada (entre 45 e 60 segundos), característica perfeitamente condizente e intrínseca à avaliação técnica base sem perdas do mérito e desempenho principal na fase de análise do serviço (SaaS Pilot).
