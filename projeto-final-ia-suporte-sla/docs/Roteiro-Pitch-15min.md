# Roteiro do pitch — 15 minutos

Script de ensaio para [`Pitch_15min.pptx`](Pitch_15min.pptx). Cada bloco traz **⏱ tempo
acumulado**, **🎤 quem fala**, **🖥 o que está na tela** e **🗣 o texto**.

O texto não é para decorar palavra por palavra — é para você saber *exatamente* qual é a
ideia de cada slide e não se perder. Decore só os **números em negrito**.

## Divisão

| Quem | Slides | Tempo | Assunto |
|---|---|---|---|
| **Pedro Felipe** | 1, 2, 10, 11, 12 | ~5 min | Abertura, problema, dashboard, nuvem, fecho |
| **João Paulo** | 3, 4, 5, 6, 7 | ~6 min | Arquitetura, dados, vazamento, dbt, Airflow |
| **Rogério** | 8, 9 | ~3 min | Modelos, métricas, matriz de confusão |

> Regra de ouro: **quem não está falando não interrompe.** Anotem dúvidas e respondam no
> final. Nada consome mais tempo que três pessoas se sobrepondo.

---

## Slide 1 · Capa
**⏱ 0:00 – 0:30 · 🎤 Pedro Felipe**

> "Boa noite. Nosso projeto integra as três disciplinas do módulo num problema só:
> **prever quais chamados de suporte técnico vão estourar o prazo de SLA**, para que o
> gestor priorize a fila antes de o prazo vencer. Em 15 minutos vamos do problema ao
> painel de decisão, passando pelo pipeline de dados, pelo modelo e pela nuvem."

*Não leia os nomes do grupo — eles estão na tela.*

---

## Slide 2 · O gestor decide no escuro
**⏱ 0:30 – 2:00 · 🎤 Pedro Felipe**

> "Numa central de suporte, todo chamado tem um prazo contratual de resolução — o SLA.
> No nosso caso: **crítico 4 horas, alto 8, médio 24, baixo 48**. Estourar custa multa,
> insatisfação e, no limite, cancelamento de contrato.
>
> Hoje o gestor prioriza a fila olhando só a prioridade cadastrada no chamado. E nós
> medimos o quanto essa regra funciona: ela acerta **apenas 50% dos alertas que emite** e
> **deixa passar 37% das violações reais**.
>
> Nossa proposta é dar a ele um risco previsto por chamado, calculado logo após a primeira
> resposta do agente, para reordenar a fila **por risco** e não por prioridade. É o primeiro
> momento em que já existe informação suficiente e ainda há tempo de agir."

**Transição:** *"O João Paulo vai mostrar como o dado chega até esse modelo."*

---

## Slide 3 · A arquitetura
**⏱ 2:00 – 3:30 · 🎤 João Paulo**

> "É um pipeline **ELT** em sete etapas, organizado em três camadas.
>
> ELT e não ETL: carregamos o dado bruto primeiro e transformamos **dentro** do warehouse,
> com SQL versionado no dbt. A transformação deixa de ser um script escondido e vira código
> revisável e testável.
>
> As camadas: **bronze** com as três fontes brutas; **prata** com os dados limpos e os
> atributos extraídos; **ouro** com o modelo dimensional do dbt.
>
> E um detalhe de engenharia: o `run_pipeline.py` e a DAG do Airflow executam as mesmas sete
> etapas. Não existe uma versão do código para rodar local e outra para orquestrado."

---

## Slide 4 · Três tipos de dado, uma tabela só
**⏱ 3:30 – 5:00 · 🎤 João Paulo**

> "O enunciado exige dados estruturados mais pelo menos uma fonte não estruturada. Temos as
> três categorias.
>
> **Estruturado**: a tabela de chamados, com categoria, prioridade, canal, tier e tempos.
> **Não estruturado**: o texto livre que o cliente escreveu. **Semiestruturado**: o log de
> eventos de cada chamado, uma lista aninhada em JSON.
>
> Do texto extraímos nove atributos numéricos — tamanho, contagem de palavras de urgência,
> proporção de maiúsculas, que é um jeito de medir se o cliente está exaltado, e marcadores
> de reembolso, cancelamento e erro. Dos logs, três agregações.
>
> Um cruzamento pelo identificador do chamado junta tudo: **8.000 chamados, 26 colunas**.
> E **22,8% violam o SLA** — a classe que nos interessa é minoria, e isso vai importar na
> hora de escolher a métrica."

*Se perguntarem por que os dados são sintéticos:* reprodutibilidade e privacidade. Qualquer
pessoa clona e roda sem credencial, e texto real de suporte tem dado pessoal. O esquema
espelha o Customer Support Ticket Dataset; trocar os arquivos em `data/raw` usa dados reais.

---

## Slide 5 · A decisão que sustenta o projeto
**⏱ 5:00 – 6:00 · 🎤 João Paulo**

> "Este é o slide mais importante da nossa apresentação.
>
> Olhem o que **não** entra como atributo: o tempo de resolução e a nota de satisfação.
>
> O tempo de resolução está fora porque **o alvo é calculado a partir dele**. Se usássemos,
> o modelo teria quase 100% de acurácia e seria inútil — no momento da decisão o chamado
> ainda não foi resolvido, esse número não existe. A nota de satisfação, idem: só é
> preenchida depois que o chamado fecha.
>
> A regra que aplicamos: **só entra o que já é conhecido no momento da decisão**. E fomos
> além — a média e o desvio da padronização são calculados só no conjunto de treino. É um
> vazamento sutil, muito comum, que infla a métrica sem ninguém perceber."

---

## Slide 6 · Modelagem e qualidade
**⏱ 6:00 – 7:30 · 🎤 João Paulo**

> "No dbt, a camada de staging só padroniza tipos. Acima dela, quatro dimensões e dois
> fatos. O `fct_tickets` é o fato central: um registro por chamado, integrando as três
> fontes. E o `mart_ticket_decision` traduz a probabilidade do modelo em faixa de risco —
> Alto, Médio, Baixo — que é o que o gestor consegue usar sem entender de estatística.
>
> São **12 modelos e 10 testes** de qualidade: unicidade, não-nulo, valores aceitos e
> integridade referencial. O enunciado pedia dois. Tudo passa: **PASS igual a 22**.
>
> E aqui está algo que descobrimos por acidente: rodamos os mesmos modelos em **DuckDB e em
> Postgres**, com PASS=22 nos dois, sem mudar uma linha de SQL — só o `--target`. Foi isso
> que revelou o único trecho não portável do projeto, um `cast as double` que só existe no
> DuckDB, e que trocamos pelo tipo padrão ANSI. Nossa modelagem é **agnóstica de
> warehouse**, e é o mesmo mecanismo que aponta para o Snowflake."

---

## Slide 7 · Orquestração em execução
**⏱ 7:30 – 8:30 · 🎤 João Paulo**

> "Esta é a DAG rodando no Airflow. Sete tasks encadeadas, agendamento diário, retry
> automático por task. À esquerda, o histórico: três execuções, todas verdes.
>
> O ganho sobre rodar um script é operacional: se o dbt falhar às três da manhã, o Airflow
> tenta de novo sozinho e permite reprocessar **só aquela etapa**, sem refazer a ingestão.
>
> Uma decisão técnica: usamos `BashOperator` porque o Airflow e o dbt têm dependências
> incompatíveis — o Airflow exige SQLAlchemy 1.4 e protobuf 4; o dbt exige protobuf 6. Em
> vez de forçar convivência, o Airflow **orquestra** e cada etapa roda isolada no ambiente
> do projeto. É como se faz em produção."

**Transição:** *"O Rogério assume, com o modelo."*

---

## Slide 8 · O modelo, medido contra a prática atual
**⏱ 8:30 – 11:00 · 🎤 Rogério**

> "A tarefa é classificação binária: o chamado vai violar o prazo, sim ou não. Dividimos
> **6.000 para treino e 2.000 para teste**, de forma estratificada, com 49 atributos.
>
> Antes de qualquer modelo, duas réguas. A primeira: chutar sempre 'não viola' já dá
> **77% de acurácia** — por isso acurácia sozinha, aqui, engana. A segunda, que é a que
> importa: a regra que o gestor usa hoje, com **F1 de 0,556**. É essa a barra a superar.
>
> O enunciado exige o mesmo algoritmo implementado à mão e com biblioteca. Escolhemos o
> **KNN**: calcula a distância até todos os exemplos de treino, pega os 15 vizinhos mais
> próximos e faz uma votação. Implementamos em NumPy puro, em 37 linhas.
>
> E o resultado é a nossa melhor evidência: as duas versões deram **concordância de 100%**
> nas 2.000 predições. Nenhum chamado classificado diferente. Isso prova que entendemos o
> algoritmo por dentro, não só chamamos uma função.
>
> Comparamos ainda com uma rede neural, o **MLP**, com duas camadas ocultas de 64 e 32
> neurônios. Ele venceu, com **F1 de 0,756 e AUC de 0,944**, e virou o modelo de produção —
> a escolha é automática no código: vence o maior F1.
>
> O número que importa para o negócio: o F1 sai de **0,556 para 0,756** — **36% melhor** que
> a prática atual."

*Por que F1 e não acurácia:* é a média harmônica de precisão e recall, e num problema com
classe minoritária é ela que mostra se o modelo realmente acha os positivos.

---

## Slide 9 · O que isso significa na operação
**⏱ 11:00 – 11:45 · 🎤 Rogério**

> "Traduzindo a matriz de confusão: dos **456 chamados que realmente violaram**, o modelo
> avisou sobre **349** a tempo. **107 escaparam**, e houve **118 alarmes falsos**.
>
> Priorizamos recall de propósito — e o nosso é **0,765**: um falso negativo é um prazo
> estourado sem ninguém ser avisado, o que é caro. Um falso positivo é um agente que olhou
> um chamado à toa, o que é barato. Errar para mais, aqui, é o erro certo a cometer."

**Transição:** *"E é o Pedro que mostra onde isso vira decisão."*

---

## Slide 10 · O painel onde a decisão acontece
**⏱ 11:45 – 13:15 · 🎤 Pedro Felipe**

> "Este é o Metabase conectado ao warehouse. Dez cards e três filtros — prioridade,
> categoria e canal.
>
> No topo, os indicadores: 8.000 chamados, 22,8% de violação, 14,2 horas de resolução média.
> Abaixo, a violação por prioridade, por categoria, por canal e a evolução mensal. E, mais
> abaixo, a **fila priorizada por risco** — os chamados que o gestor ataca primeiro — e a
> matriz de confusão, que está no painel de propósito: ele precisa saber o quanto pode
> confiar antes de agir.
>
> Mas o achado mais acionável é este: **'Solicitação de Recurso' viola 68,5% das vezes**,
> enquanto 'Dúvida' viola meio por cento. Isso não é um problema de previsão, é de
> processo: pedido de funcionalidade nova depende do time de produto, não do suporte, e não
> deveria dividir a mesma fila e o mesmo prazo."

*Se sobrar tempo, aplique um filtro ao vivo:* escolha Prioridade = Crítica e mostre o número
saltar de **22,8% para 60,4%**.

---

## Slide 11 · Nuvem: o que é real e o que é proposta
**⏱ 13:15 – 14:15 · 🎤 Pedro Felipe**

> "Este é o diagrama da arquitetura equivalente 100% em AWS: Lambda na ingestão, S3 em três
> camadas, Snowflake, dbt, SageMaker no modelo e Metabase servindo o painel, com o Airflow
> gerenciado orquestrando e CloudWatch, IAM e CloudFormation atravessando tudo.
>
> E quero ser transparente sobre o escopo. **Implementado**: o template CloudFormation, que
> provisiona os três buckets com versionamento e criptografia, o papel IAM, a Lambda de
> ingestão e o agendamento. Fizemos também um template específico para o AWS Academy, porque
> o laboratório não permite criar IAM Roles — ele reaproveita o LabRole.
>
> **Proposta**, e marcada como tal no diagrama: o Airflow gerenciado, o SageMaker e o
> Snowflake gerenciado.
>
> Sobre custo: o que rodamos ficou dentro do nível gratuito. A arquitetura completa custaria
> entre **450 e 600 dólares por mês** — o Airflow gerenciado sozinho passa de 350. Numa
> versão enxuta, cai para **70 a 120 dólares**."

---

## Slide 12 · Fechamento
**⏱ 14:15 – 15:00 · 🎤 Pedro Felipe**

> "Fechando: a solução apoia três decisões concretas. **Priorizar a fila**, atacando os 447
> chamados de risco alto. **Realocar agentes** para crítica e alta, onde 60% e 47% dos
> chamados estouram. E **agir na estrutura**, separando solicitação de recurso da fila de
> suporte.
>
> E as limitações, que assumimos: os dados são sintéticos, então as métricas são otimistas;
> o modelo entrega probabilidade, mas não fizemos teste formal de calibração; o modelo é estático,
> sem retreino nem monitoramento de drift; e o painel usa histórico, não uma fila em tempo
> real.
>
> Obrigado. Ficamos à disposição para as perguntas."

---

## O que NÃO dizer

Três armadilhas que custam credibilidade se a banca perceber:

1. **Não diga que "usamos o Snowflake".** Diga: *"a modelagem dbt é agnóstica de warehouse;
   provamos em DuckDB e Postgres, e o profile do Snowflake está pronto — falta credencial."*
2. **Não diga que "enviamos os dados para o S3".** O código existe e o CloudFormation está
   pronto, mas o upload não foi executado. Diga *"implementado e pronto para executar"*.
3. **Não diga que o modelo "tem 90% de acurácia"** sem contexto. O baseline burro já tem 77%.
   Fale sempre em **F1 contra a régua de 0,556**.

Assumir a limitação antes da pergunta vale mais que ser pego nela.

---

## Perguntas prováveis (resposta em uma frase)

| Pergunta | Resposta |
|---|---|
| Por que dados sintéticos? | Reprodutibilidade e privacidade; o esquema espelha um dataset real e basta trocar os arquivos. |
| Por que DuckDB e não Snowflake? | É espelho local; a mesma modelagem dbt roda nos dois, provamos rodando também em Postgres. |
| Como evitaram vazamento? | O ponto de decisão é após a 1ª resposta; desfechos ficam fora, e a padronização usa só o treino. |
| Por que o KNN foi o pior? | Desbalanceamento: entre 15 vizinhos, a maioria é da classe majoritária e a votação puxa para o negativo. |
| Por que o MLP venceu? | Rede neural com 2 camadas ocultas capta interações não lineares entre os atributos; melhor F1 e melhor recall. |
| Essa probabilidade é calibrada? | O MLP entrega probabilidade real via `predict_proba`, mas não rodamos teste de calibração — usamos para ranquear a fila. |
| Tem overfitting? | Todas as métricas são do conjunto de teste; quatro famílias de modelo deram resultados coerentes. |
| O que é PASS=22? | 12 modelos mais 10 testes do dbt, todos aprovados. |
| Quantos testes dbt? | Dez: unicidade, não-nulo, valores aceitos e integridade referencial. O mínimo pedido era dois. |

---

## Plano de ensaio

**Ensaio 1 — individual, sem cronômetro.** Cada um lê seus slides em voz alta, sozinho, duas
vezes. O objetivo é achar as frases que travam a língua e reescrevê-las com suas palavras.

**Ensaio 2 — individual, com cronômetro.** Se o seu bloco estoura o tempo, corte exemplos,
nunca os números.

**Ensaio 3 — completo, com cronômetro e sem parar.** Mesmo se alguém errar, siga até o fim.
Anote onde perdeu tempo.

**Ensaio 4 — para alguém de fora.** Alguém que não conhece o projeto. Peça que anote toda
pergunta que surgir; essas são as perguntas que a banca vai fazer.

### Marcos de tempo para conferir no relógio

| Momento | Deve estar em |
|---|---|
| Fim do slide 2 (problema) | 2:00 |
| Fim do slide 5 (vazamento) | 6:00 |
| Fim do slide 7 (Airflow) | 8:30 |
| Fim do slide 9 (matriz) | 11:45 |
| Fim do slide 11 (nuvem) | 14:15 |

Se aos 8:30 você ainda não terminou o Airflow, **corte a explicação do BashOperator** no
slide 7 e o exemplo de atributos de texto no slide 4. São os dois cortes mais baratos.

### Antes de apresentar

- [ ] `docker compose -f infra/docker-compose.yml up -d` (Metabase, caso mostre ao vivo)
- [ ] `airflow standalone` (caso mostre a DAG ao vivo)
- [ ] Deck aberto em tela cheia, notebook no carregador, notificações silenciadas
- [ ] Alguém do grupo com o cronômetro visível
