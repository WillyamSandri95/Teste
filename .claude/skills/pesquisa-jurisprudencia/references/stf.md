# STF — rota de pesquisa

O portal `https://jurisprudencia.stf.jus.br` é aberto, sem bloqueio. É uma aplicação de página única: o formulário resiste a preenchimento programático, mas **a busca inteira cabe na URL**, e navegar direto para ela funciona de forma confiável. Use essa via.

## URL de busca

```
https://jurisprudencia.stf.jus.br/pages/search
  ?base=acordaos
  &pesquisa_inteiro_teor=false
  &sinonimo=true&plural=true&radicais=false&buscaExata=true
  &page=1&pageSize=50
  &queryString=<expressão percent-encoded>
  &sort=_score&sortBy=desc
```

Navegue com a ferramenta de navegador, aguarde de 5 a 10 segundos e leia a página. A expressão precisa ser percent-encoded (`encodeURIComponent`).

Bases úteis em `base=`: `acordaos` (padrão), `decisoes` (monocráticas), `sumulas`, `informativo`. Comece sempre por `acordaos` — o volume de monocráticas é uma ordem de grandeza maior e raramente ajuda.

Ordene por `_score` para relevância; troque para data quando o que importa for o estado atual do entendimento.

## Operadores

`"termo exato"` · `e` · `ou` · `nao` · `adj` · `prox` · `$` (truncamento) · `?` (curinga de caractere) · `( )` para agrupar.

```
"responsabilidade civil do Estado" e omiss$
"repercussão geral" e (prescrição adj2 quinquenal)
```

## O que extrair — e por que é a parte mais valiosa

Cada resultado de repercussão geral traz, além da ementa, dois campos próprios:

- **Tema** — número e enunciado da controvérsia
- **Tese** — o texto da tese fixada, literal

A tese é o que vincula. Transcreva-a sempre que existir, entre aspas, e identifique o tema pelo número.

O painel lateral informa quantos resultados são de repercussão geral. Esse recorte costuma ser o mais relevante de toda a pesquisa: um punhado de temas de RG diz mais sobre a posição da Corte do que dezenas de acórdãos de turma.

Para varrer os temas de uma vez, é prático extrair da página com um pequeno trecho de JavaScript, capturando os blocos `Tema\n<n> - <título>\n\nTese\n<texto>`.

Atenção à distinção entre **"Repercussão Geral – Mérito"** (tese fixada, é o que interessa) e **"Repercussão Geral – Admissibilidade"** (apenas reconheceu a repercussão; ainda não há tese). Citar uma admissibilidade como se fosse tese firmada é erro grave.

Alguns temas fixam justamente que a matéria é **infraconstitucional** — isso não é uma tese de mérito sobre o direito material, é uma barreira recursal. Útil, mas não confunda os dois.

## Inteiro teor

Cada resultado traz link próprio para o acórdão. Abra quando precisar do voto ou da modulação — a ementa do STF costuma ser mais econômica que a do STJ.
