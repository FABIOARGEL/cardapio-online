# 1. Documento de Visão

Este documento descreve o escopo estratégico, o problema que a plataforma resolve e a visão de produto para o "Cardápio Online".

---

## Sumário

- [1.1 Problema](#11-problema)
- [1.2 Objetivo](#12-objetivo)
- [1.3 Público-Alvo](#13-público-alvo)
- [1.4 Diferenciais Competitivos](#14-diferenciais-competitivos)
- [1.5 Visão do Produto](#15-visão-do-produto)

---

## 1.1 Problema

Muitos estabelecimentos gastronômicos de pequeno e médio porte enfrentam desafios técnicos e financeiros para digitalizar suas operações. Os principais gargalos identificados incluem:

* **Cardápios Físicos Desatualizados:** A alteração de preços ou a inclusão de novos produtos exige a reimpressão constante de materiais, gerando custos adicionais e atrito na atualização do cardápio.
* **Ausência de Presença Digital Autônoma:** Uma parcela significativa de estabelecimentos não possui infraestrutura digital própria, dependendo exclusivamente de redes sociais ou ferramentas genéricas de mensagens.
* **Dependência e Custos Elevados de Marketplaces:** A utilização de plataformas consolidadas de delivery impõe taxas abusivas (frequentemente entre 12% e 27% sobre as vendas), reduzindo drasticamente as margens de lucro dos restaurantes.
* **Experiência do Consumidor Fragmentada:** Os clientes necessitam alternar entre múltiplas aplicações e canais para buscar estabelecimentos, visualizar opções e efetuar pedidos.
* **Gestão Operacional Manual:** A captação de pedidos via telefone ou mensagens textuais não estruturadas aumenta a margem de erros, gera ineficiência operacional e impacta diretamente a receita.

---

## 1.2 Objetivo

Desenvolver uma **plataforma SaaS (Software as a Service) centralizada, multi-tenant e escalável** que viabilize:

### Para Gestores de Restaurantes (Tenants)
* Cadastro, configuração e gestão autônoma de cardápios digitais interativos.
* Recepção e processamento de pedidos online com sincronização em tempo real via WebSocket.
* Atualização imediata de disponibilidade de produtos, imagens e precificação.
* Acesso a painéis analíticos com métricas de vendas, faturamento e performance de produtos.

### Para Consumidores Finais
* Navegação fluida em um ecossistema integrado que abriga múltiplos estabelecimentos.
* Visualização detalhada de produtos com fotografias de alta qualidade, categorização semântica e descrições claras.
* Fluxo de checkout intuitivo, permitindo a construção de carrinhos de compras eficientes.
* Rastreamento do status de preparação e entrega do pedido em tempo real.

---

## 1.3 Público-Alvo

A plataforma atende a duas personas distintas no ecossistema de food service.

### Donos de Restaurantes (Tenants)

| Atributo | Descrição |
| --- | --- |
| **Perfil** | Proprietários e gerentes de lanchonetes, pizzarias, hamburguerias e restaurantes locais. |
| **Porte Operacional** | Micro, pequeno e médio porte (1 a 50 colaboradores). |
| **Ponto de Dor Principal** | Erosão das margens de lucro por taxas de marketplaces e falta de controle sobre os dados dos clientes. |
| **Necessidade Tecnológica** | Interface administrativa simplificada que entregue autonomia sem exigir conhecimento técnico avançado. |

### Consumidores Finais

| Atributo | Descrição |
| --- | --- |
| **Perfil** | Consumidores digitais que buscam praticidade, velocidade e clareza no processo de alimentação. |
| **Comportamento** | Tendência a comparar visualmente opções antes da tomada de decisão de compra. |
| **Necessidade Tecnológica** | Experiência de uso baseada em "Mobile-First", interface ágil de carregamento rápido e feedback visual imediato. |

---

## 1.4 Diferenciais Competitivos

O sistema se posiciona no mercado através de vantagens arquiteturais e de modelo de negócios:

* **Arquitetura Multi-Tenant:** Centralização de múltiplos restaurantes em uma única infraestrutura base baseada em isolamento lógico de dados.
* **Modelo Financeiro Previsível (SaaS):** Estrutura de cobrança por assinatura (flat-fee) que elimina a retenção percentual sobre o Volume Bruto de Mercadorias (GMV) do lojista.
* **Sincronização Bidirecional em Tempo Real:** Utilização de WebSockets para eliminar o delay entre a requisição do cliente e o terminal do restaurante.
* **Fricção Zero no Onboarding:** Autenticação delegada via provedores de identidade OAuth (Google) maximizando as taxas de conversão de cadastro.
* **Gestão Elástica de Mídia:** Armazenamento em nuvem distribuída (AWS S3) garantindo performance de entrega de imagens (Edge Caching) e alta disponibilidade.
* **Autonomia e White-label Parcial:** Capacidade do lojista personalizar a identidade visual primária do seu espaço digital na plataforma.

---

## 1.5 Visão do Produto

> *"Consolidar-se como a infraestrutura digital primária para operações de food service locais, democratizando o acesso a tecnologias de vendas online de alta performance e devolvendo o controle da jornada e da rentabilidade aos proprietários."*

### Roadmap Estratégico

#### Fase 1: Minimum Viable Product (MVP)
* Suporte completo a múltiplos tenants e gestão de catálogo.
* Visualização pública e motor de busca integrado.
* Fluxo de carrinho de compras assíncrono.
* Integração de autenticação OAuth (Google).
* Integração de infraestrutura cloud para upload de imagens.

#### Fase 2: Escala e Retenção
* Dashboard analítico financeiro e métricas de conversão.
* Implementação do motor de avaliações e reputação (Reviews).
* Integração direta com gateways de pagamento corporativos (Stripe/Pagar.me).

#### Fase 3: Maturidade e Expansão
* Desenvolvimento de aplicações nativas iOS e Android (React Native).
* Motor de promoções avançadas e programas de fidelização de clientes.
* Recomendação baseada em Machine Learning para cross-selling (Sugestões Inteligentes).
* Integração nativa com operadores logísticos de last-mile delivery.
