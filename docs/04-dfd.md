# 4. Diagramas de Fluxo de Dados (DFD)

A modelagem de Fluxo de Dados mapeia as fronteiras do sistema, demonstrando como as informações transitam, são processadas e armazenadas dentro da arquitetura do Cardápio Online.

---

## Sumário

- [4.1 DFD Nível 0 — Diagrama de Contexto](#41-dfd-nível-0--diagrama-de-contexto)
- [4.2 DFD Nível 1 — Decomposição de Processos](#42-dfd-nível-1--decomposição-de-processos)

---

## 4.1 DFD Nível 0 — Diagrama de Contexto

O diagrama de contexto (Nível 0) apresenta a visão arquitetural de mais alto nível, tratando todo o software como um nó único em comunicação direta com agentes externos que nutrem ou consomem dados do ecossistema.

```mermaid
flowchart TD
    %% Agentes Externos
    C["Cliente (Consumidor)"]
    G["Gestor (Restaurante)"]
    S3["AWS S3 (Object Storage)"]

    %% Sistema Central
    Sys(("Sistema SaaS\nCardápio Online"))

    %% Fluxos - Cliente
    C -- "Credenciais / Autorizações" --> Sys
    Sys -- "Tokens JWT" --> C
    C -- "Pesquisas e Compras" --> Sys
    Sys -- "Cardápios, Recibos e Tracking" --> C

    %% Fluxos - Gestor
    G -- "Credenciais / Autorizações" --> Sys
    Sys -- "Tokens JWT" --> G
    G -- "Dados Cadastrais, Cardápio, Alteração Status" --> Sys
    Sys -- "Dashboard, Listagem de Pedidos" --> G

    %% Fluxos - Infraestrutura
    Sys -- "Imagens WebP/JPEG" --> S3
    S3 -- "URLs Resolvidas (CDN)" --> Sys

```

### Entidades Externas Mapeadas

| Entidade | Natureza | Papel na Arquitetura |
| --- | --- | --- |
| **Cliente** | Usuário Humano | Consome endpoints públicos, envia solicitações de autenticação e processa intenções de compra transacionais. |
| **Gestor do Restaurante** | Usuário Humano | Manipula a base de metadados dos tenants e orquestra transições logísticas dos pedidos. |
| **AWS S3 / Storage** | Serviço Cloud Expresso | Provedor passivo que recebe blobs binários e expõe URLs de *Edge Caching*. |

---

## 4.2 DFD Nível 1 — Decomposição de Processos

O Nível 1 desestrutura a topologia monolítica do Nível 0 e apresenta como a lógica de serviço do back-end roteia as informações pelos diferentes domínios e coleções do MongoDB.

```mermaid
flowchart TD
    %% Entidades Externas
    C["Cliente"]
    G["Gestor do Restaurante"]
    S3["AWS S3"]

    %% Processos (Domínios de Serviço)
    P1(("1.0\nAuth & JWT"))
    P2(("2.0\nTenant Management"))
    P3(("3.0\nCatalog Service"))
    P4(("4.0\nDiscovery Engine"))
    P5(("5.0\nOrder Controller"))
    P6(("6.0\nFulfillment Service"))

    %% Data Stores (MongoDB)
    D1[("D1: Collection Users")]
    D2[("D2: Collection Restaurants")]
    D3[("D3: Collection Orders")]

    %% Interações Cliente
    C -- "F1: E-mail / Senha / OAuth" --> P1
    P1 -- "F2: Token de Acesso" --> C
    C -- "F3: Filtros de Busca" --> P4
    P4 -- "F4: Resposta Paginada" --> C
    C -- "F5: Payload de Checkout" --> P5
    P5 -- "F6: Número de Rastreio" --> C

    %% Interações Gestor
    G -- "F7: Metadados do Estabelecimento" --> P2
    P2 -- "F8: Feedback Visual" --> G
    G -- "F10: Sinais Operacionais" --> P6
    P6 -- "F9: Feed de Fila (Sockets)" --> G

    %% Relacionamentos de Banco de Dados (Leitura/Escrita)
    P1 <--> D1
    P2 <--> D2
    P3 <--> D2
    P5 <--> D3
    P6 <--> D3

    %% Interações de Infraestrutura
    P2 -- "F11: Blob Upload" --> S3
    S3 -- "F12: Absolute URL" --> P2
    P3 -- "F13: Blob Upload" --> S3
    S3 -- "F14: Absolute URL" --> P3

```

### Detalhamento dos Processos de Software

| Processo Interno | Domínio | Escopo e Responsabilidade Principal |
| --- | --- | --- |
| **1.0 Auth & JWT** | Autenticação | Gerencia a criação do perfil, delegação para Google OAuth, *hashing* seguro (bcrypt) e emissão temporal do JWT. |
| **2.0 Tenant Management** | Administrativo | Fornece os *endpoints* e *services* para a curadoria técnica dos restaurantes, incluindo *upload* do S3 de logos e banners. |
| **3.0 Catalog Service** | Inventário | Mantém a sanidade de dados dos produtos (Embedding no *Mongo*), categorização e formatação financeira. |
| **4.0 Discovery Engine** | Consulta | Motor de *read-only* que varre a coleção otimizada de restaurantes com paginação e processa filtros de pesquisa. |
| **5.0 Order Controller** | Checkout | Recebe o *Payload* de compra, executa snapshot das matrizes de custo financeiro e grava no Banco de Dados. |
| **6.0 Fulfillment Service** | Operacional | Controla as transições da máquina de estado do pedido, publicando o histórico contábil e orquestrando o WebSocket. |

### Detalhamento dos Data Stores (NoSQL)

| Instância | Ref. MongoDB | Arquitetura |
| --- | --- | --- |
| **D1** | `users` | Coleção central de identidades com índices únicos para `email` e *sparse index* para `google_id`. |
| **D2** | `restaurants` | Coleção densa focada em leituras, com produtos alocados via estratégia *Embedded Document Pattern*. |
| **D3** | `orders` | Coleção transacional auditável. Possui registros fixos (sem relação em cascata para produtos após o processamento da compra). |
