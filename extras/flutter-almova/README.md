# App ALMOVA (Android): mudanças sobre o app Flutter do wger

Enquanto o fork `Raynay01/flutter` não existe, as mudanças do app ficam aqui
como patches sobre o app oficial (`wger-project/flutter`, commit `b7b7f25`).
Quando o fork for criado, elas viram commits no branch `almova/app-base` do
fork e esta pasta sai.

## Aplicar

```bash
git clone https://github.com/wger-project/flutter.git almova-app
cd almova-app
git checkout b7b7f25
git checkout -b almova/app-base
git am /caminho/do/wger/extras/flutter-almova/patches/*.patch
```

## O que muda

1. **Galeria pelo endereço com login:** as fotos de progresso ficam no
   armazenamento privado do servidor; o app baixa cada foto por
   `/api/v2/gallery/{id}/file/` com o login (renovado sozinho) em vez do
   endereço público `/media/`.
2. **Marca ALMOVA:** nome ALMOVA no celular e na tela de login; identificador
   Android `br.com.almova.app`, então instala ao lado do app do wger sem
   substituí-lo. O servidor padrão do login vem da construção:
   `--dart-define=ALMOVA_SERVER=https://<endereço do servidor>`.
3. **Cartão "Acompanhamento" na tela inicial:** mostra os profissionais que
   acompanham o paciente (treino, fisioterapia, nutrição) e o próximo
   atendimento. Some quando ninguém acompanha, sem internet ou num servidor
   sem o ALMOVA. Dá para esconder nas configurações do painel, como os outros.
4. **Mensagens:** tocar num profissional no cartão abre a conversa daquele
   acompanhamento. Mostra o histórico, as fotos (baixadas com o login) e
   toca os vídeos; envia texto, foto ou vídeo (câmera ou galeria, até 50 MB)
   enquanto o acompanhamento está aberto e marca como lidas as mensagens do
   profissional. O vídeo recebido é baixado com o login para um arquivo
   temporário, apagado ao fechar o vídeo.
5. **Agenda:** tocar no próximo atendimento abre as próximas consultas (data,
   tipo, profissional, duração, local e observações). Dá para cancelar, com
   confirmação; o profissional é avisado.
6. **Sem relato público de erro:** o app do wger oferecia abrir um relato no
   GitHub público com os registros do app, que podem citar dados de saúde.
   No ALMOVA isso está desligado; copiar os registros continua, para mandar
   ao suporte em particular.
7. **Login pelo navegador volta por `almova://`:** com `wger://`, o app do
   wger no mesmo celular poderia receber o token. O servidor manda o esquema
   de `APP_AUTH_SCHEME` (`almova` em produção).
8. **Textos com ALMOVA:** em inglês e português, o app fala ALMOVA onde
   falava wger (login, servidor, avisos). O "Sobre" mantém o crédito ao wger.
9. **Convites:** os convites pendentes aparecem no cartão "Acompanhamento",
   com o texto de consentimento do site. "Aceitar e autorizar" registra o
   consentimento no servidor; "Recusar" encerra o convite.
10. **Fisioterapia de hoje:** para quem tem fisioterapeuta, o cartão abre os
    exercícios do protocolo do dia (séries, repetições, carga, onde fazer,
    instruções e vídeo) com "Marcar como feito", e o registro de dor de 0 a 10
    no momento que o fisioterapeuta pediu. A dor alimenta os alertas dele.
11. **Ícone, logos e tela de abertura provisórios:** a marca do site (A
    azul-marinho sobre quadrado verde-neon) no ícone do Android, no ícone de
    notificação, no login, no "Sobre" e na abertura. Trocar pelo logotipo
    oficial quando existir (o ícone do iOS ainda é o do wger).
12. **Privacidade e exclusão da conta:** nas configurações, "Privacidade e seus
    dados" pede a exclusão da conta (digitando EXCLUIR), permite desistir e
    lista os pedidos; "Baixar meus dados" abre a página do site. A Play Store
    exige a exclusão dentro do app.
13. **Alimentação do dia:** para quem tem nutricionista, o cartão abre as
    calorias e os macronutrientes contra as metas, a água (+200/+300/+500 ml)
    e as refeições do plano com "Segui" (lança os itens no diário),
    "Segui parcialmente" e "Não segui".
14. **Compartilhamento:** no cartão, um interruptor por profissional e por
    dado (rotina de treino, diário, dor, peso e medidas, observações); a área
    do próprio profissional não aparece. Ligar e desligar fica registrado como
    consentimento no servidor.
15. **Avisos no celular:** depois do login o app pede permissão e registra o
    celular no servidor para os avisos (mensagem nova, consulta marcada,
    mudada ou cancelada, plano publicado). Tocar no aviso abre a conversa ou a
    agenda; um aviso com o app aberto aparece na parte de baixo da tela. Na
    saída da conta o celular é removido antes, para a próxima pessoa no
    aparelho não receber os avisos. Desligado até a construção receber os
    dados do projeto Firebase (veja abaixo).

## Construir o APK

Flutter 3.47.9 e o SDK do Android (plataforma `android-37.0`, build-tools
37.0.0, NDK 28.2.13676358).

```bash
flutter build apk --release --split-per-abi \
  --dart-define=ALMOVA_SERVER=https://<endereço do servidor>
```

Com os avisos no celular, acrescente os dados do app Android do projeto
Firebase (no console: Configurações do projeto > Seus apps, app com o pacote
`br.com.almova.app`; são identificadores públicos, não senhas):

```bash
  --dart-define=FCM_API_KEY=<apiKey> \
  --dart-define=FCM_APP_ID=<mobilesdk_app_id> \
  --dart-define=FCM_SENDER_ID=<project_number> \
  --dart-define=FCM_PROJECT_ID=<project_id>
```

O servidor envia com a conta de serviço do mesmo projeto
(`extras/docker/almova/README.md`, "Celular (push)").

A chave de assinatura fica em `fastlane/metadata/envfiles/key.properties`
(fora do Git). Para publicar na Play Store é preciso a chave definitiva do
ALMOVA, guardada fora do repositório.

## Verificação

- `flutter analyze` sem problemas; os 2.212 testes do app passam (eram 2.187 no app oficial).
- Contra o servidor local: o código do app entrou, enviou uma foto, baixou a
  mesma foto byte a byte; outra conta foi recusada; a foto ficou só na pasta
  privada.
- Contra o servidor local: o cartão achou a fisioterapeuta e o próximo
  retorno; a conversa recebeu a mensagem com foto (a mesma foto, byte a byte),
  enviou uma resposta com acentos e marcou a mensagem da profissional como lida.
- APK de teste (`app-arm64-v8a-release.apk`, 38,2 MB): identificador
  `br.com.almova.app`, nome ALMOVA, assinado com uma chave de teste. Não foi
  aberto num celular: este ambiente não tem emulador Android.
