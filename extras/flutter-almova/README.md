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
   avisa dos vídeos; envia texto enquanto o acompanhamento está aberto e marca
   como lidas as mensagens do profissional. Enviar foto ou vídeo pelo app e
   tocar vídeos ficam para a próxima etapa.

## Construir o APK

Flutter 3.47.9 e o SDK do Android (plataforma `android-37.0`, build-tools
37.0.0, NDK 28.2.13676358).

```bash
flutter build apk --release --split-per-abi \
  --dart-define=ALMOVA_SERVER=https://<endereço do servidor>
```

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
