# ALMOVA de teste no GitHub Codespaces (grátis, sem servidor)

O GitHub empresta um computador na nuvem, aberto pelo navegador. O ALMOVA roda
nele e ganha um endereço com HTTPS que abre no celular: dá para entrar com
Google e instalar como app.

**Só dados de teste.** O Codespace fica fora do Brasil, desliga quando fica sem
uso e é apagado depois de 30 dias parado. Para pacientes de verdade, use um
servidor (`HOMOLOGACAO-GRATUITA.md`).

## Antes: conferir que não há cobrança

Em **github.com/settings/billing**, na parte de limites de gastos (*Spending
limits* / *Budgets*), o Codespaces deve estar em **US$ 0**, que é o padrão.
Assim, quando a cota grátis do mês acaba, ele só para, sem cobrar.

## 1. Criar o Codespace (5 min)

1. Entre no GitHub com a sua conta e abra o repositório
   **github.com/Raynay01/wger**.
2. No botão de branch (à esquerda, acima da lista de arquivos, mostra
   `master`), escolha **`claude/happy-goldberg-8nupoc`**. Esse passo é
   importante: o ALMOVA de teste só existe nesse branch.
3. Clique no botão verde **Code** > aba **Codespaces** > **Create codespace on
   claude/happy-goldberg-8nupoc**.
4. Em alguns minutos abre um editor (VS Code) no navegador, com um
   **Terminal** embaixo. No alto, ao lado do nome, ele deve mostrar
   `claude/happy-goldberg-8nupoc`.

Se o comando do passo 2 responder "No such file or directory", o Codespace foi
criado no branch errado: apague (github.com/codespaces > **...** > **Delete**) e
crie de novo escolhendo o branch.

## 2. Instalar o ALMOVA (1 comando, 20 a 30 min esperando)

No terminal, cole:

```bash
bash extras/docker/almova/codespaces.sh
```

O script mostra o **endereço** do seu ALMOVA de teste (algo como
`https://nome-do-codespace-8080.app.github.dev`) e espera o **ID do cliente
Google**. Deixe o terminal esperando e faça o passo 3.

## 3. Login com Google (10 min, em outra aba)

Siga o passo 4 de `HOMOLOGACAO-GRATUITA.md`, com uma diferença: em **Origens
JavaScript autorizadas**, coloque **o endereço que o script mostrou**. Copie o
ID do cliente (termina em `.apps.googleusercontent.com`), volte ao terminal,
cole e aperte Enter.

O script constrói e sobe tudo, carrega os exercícios e a tabela TACO, e no fim
mostra **"Abra no celular: https://..."**.

Se ele disser que não conseguiu tornar a porta pública: na aba **PORTAS**
(embaixo, ao lado do Terminal), clique com o botão direito na porta **8080** >
**Visibilidade da porta** > **Pública**.

## 4. Usar e instalar no celular

Igual à seção 6 de `HOMOLOGACAO-GRATUITA.md`: abra o endereço, **Entrar com
Google**, e instale como app (Android: **Instalar o app**; iPhone, no Safari:
**Compartilhar > Adicionar à Tela de Início**).

## Quando ele desliga

- O Codespace desliga sozinho depois de um tempo sem uso (30 minutos por padrão;
  dá para aumentar até 4 horas em **github.com/settings/codespaces > Default
  idle timeout**). Desligado, o site sai do ar.
- Para voltar: **github.com/codespaces**, clique no seu Codespace. Em um ou dois
  minutos o ALMOVA sobe sozinho, com os mesmos dados e o mesmo endereço.
- A cota grátis é de horas de uso por mês; parado, ele só ocupa espaço. Se for
  ficar semanas sem testar, apague o Codespace (menu **...** > **Delete**) e
  crie de novo depois (refazendo os passos 2 e 3, com o novo endereço no
  Google).

## Atualizar depois de mudanças minhas

No terminal do Codespace:

```bash
git pull && bash extras/docker/almova/codespaces.sh
```
