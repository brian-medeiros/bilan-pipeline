# Revisão para entrega

Revisão em 16/09/2026 da implementação local e da branch `main` de
https://github.com/brian-medeiros/bilan-pipeline.

## Parecer

A implementação local tem uma base técnica defensável para a seletiva: execução
reproduzível, evidências por valor, omissões explícitas e validações automatizadas.
A versão publicada ainda está incompleta e não permite reproduzir a execução.
Isso impede recomendar a entrega do link no estado observado.

## Estado observado no GitHub

A árvore pública continha apenas oito arquivos: `.env.example`, `.gitattributes`,
`.gitignore`, `NOTICE.md`, `README.md`, `pyproject.toml`, `requirements.txt` e
`results.json`. A consulta de PRs não retornou nenhum resultado.

Faltam publicar as pastas `bilan_pipeline/`, `tests/`, `reports/`, `docs/`,
`challenges/`, `tools/` e `data/`, necessárias para a entrega completa descrita no
README. O README revisado pressupõe que essas pastas acompanhem a publicação.
O arquivo remoto `NOTICE.md` deve ser preservado; não substituir o histórico remoto
à força para sincronizar a cópia local.

## Alterações preparadas localmente

- README resumido, com instalação, resultados e decisões antes dos detalhes.
- Detalhes técnicos preservados em `docs/TECHNICAL_NOTES.md`.
- Declaração de IA reduzida a um parágrafo com escopo, validação e erros concretos.
- Instruções antigas para criar um repositório vazio removidas do README.

Nenhuma alteração desta revisão foi enviada ao GitHub.

## Validação local

- 45 testes passaram.
- Validação do `results.json`: zero erros.
- Links relativos dos dois documentos revisados apontam para arquivos existentes.
- Nenhuma alteração no algoritmo ou nos valores extraídos nesta revisão.

## Antes da entrega

1. Publicar a implementação completa em uma branch e abrir um PR no próprio
   repositório, preservando os arquivos já publicados. Revisar o diff antes do envio.
2. Testar um clone novo com os comandos do README para confirmar que nenhum arquivo
   necessário ficou apenas no ambiente local.
3. Conferir pessoalmente valores e caixas nos PDFs: um valor direto, um cálculo de
   pessoal, uma página rotacionada e a distinção entre EUR e kEUR em Bernachon.
   Registrar apenas verificações realmente realizadas na seção de IA.
4. Solicitar revisão a `@YassineBouderbala` e `@AleBastos25`, como pede o desafio.

## Pontos para explicar na entrevista

- Por que 65% é cobertura, e não precisão; por que campos foram omitidos.
- Como o OCR em pixels a 300 dpi vira uma caixa normalizada.
- Como distinguir exercício corrente, N-1, valor bruto e valor líquido.
- Por que uma reconciliação pode passar mesmo com dois valores OCR errados.
- Por que COGS tem cobertura baixa e quais interpretações financeiras foram adotadas.
- O que o custo de API zero inclui e o que ele não mede.

O desafio permite IA e exige uma descrição honesta do uso. Uma declaração curta
é suficiente; atribuir ao candidato revisões feitas somente pela ferramenta não é.
