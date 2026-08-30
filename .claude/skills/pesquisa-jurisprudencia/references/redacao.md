# Como redigir o resultado

O que distingue uma pesquisa útil de uma lista de ementas é a **leitura**: o que os três tribunais dizem entre si, onde convergem, onde divergem, e o que isso significa para quem vai decidir. Este arquivo trata dessa parte.

## O princípio que organiza tudo: hierarquia da autoridade

Nem todo julgado pesa igual, e apresentar tudo no mesmo plano é o erro mais comum e mais custoso. A ordem:

1. **Súmula vinculante e controle concentrado** (ADI, ADC, ADPF) — vinculam.
2. **Tese de repercussão geral e de recurso repetitivo** — observância obrigatória (art. 927, III, do CPC).
3. **IRDR e IAC** — vinculam no âmbito do tribunal que os fixou. Um IRDR do TJSC vincula o TJSC.
4. **Súmulas dos tribunais** — STF, STJ e as do próprio TJSC.
5. **Órgão de cúpula** — Plenário, Corte Especial, Órgão Especial, Seções, Grupos de Câmaras.
6. **Acórdãos de turma ou câmara** — persuasivos.
7. **Monocráticas e informativos** — apoio e contexto; informativo não é fonte primária.

Quando houver tese vinculante, ela abre a análise e o resto se organiza como aplicação dela. Quando não houver, diga isso com franqueza em vez de apresentar acórdão de câmara com a solenidade de precedente qualificado.

Destaque sempre, de forma visível, quando um julgado for tese de repercussão geral, repetitivo, IAC, IRDR ou súmula — no chat e no PDF. Use o bloco `::: qualificado` no Markdown do PDF.

## O diálogo entre os tribunais

Esta é a exigência central. Não basta três seções paralelas: é preciso mostrar como as posições se relacionam. Perguntas que orientam a leitura:

- Os tribunais partem da **mesma premissa**? Chegam ao mesmo resultado por caminhos diferentes? Um caso real: em responsabilidade do Estado por omissão, o STF mantém a responsabilidade objetiva e desloca o filtro para o dever específico de agir, enquanto parte do STJ trabalha com regime bifurcado (comissiva objetiva, omissiva subjetiva). O resultado converge quase sempre, mas a fundamentação não é intercambiável — e isso importa em recurso extraordinário.
- O tribunal local **aplica** o precedente superior, o **distingue**, ou decide como se ele não existisse?
- Há tese superior que o TJSC ainda não absorveu, ou julgado local que já está superado por tese posterior?
- A divergência é **de resultado** ou apenas **de formulação**? Diga qual.

Escreva isso como análise em prosa contínua, não como bullets. O leitor é magistrado: quer o raciocínio articulado, com as fontes ancorando cada afirmação.

## Posição isolada

Sinalizar isolamento é obrigação, não cortesia — é o que impede o usuário de construir uma decisão sobre base frágil. Trate como isolada quando:

- Todos os julgados favoráveis vierem de **um único órgão julgador** (uma câmara, uma turma), sobretudo se outras câmaras decidem em sentido contrário;
- A posição depender de **um único relator** e não tiver sido acompanhada por outros;
- Existir **precedente qualificado em sentido contrário**, ainda que o julgado localizado seja mais recente;
- O julgado tiver **voto vencido** relevante, ou for de órgão fracionário contra orientação da cúpula;
- O conjunto for **muito pequeno em relação ao volume** do acervo sobre o tema.

Diga com todas as letras: "a posição encontrada está concentrada na Terceira Câmara de Direito Público e não localizei julgados de outras câmaras no mesmo sentido". Não suavize. E não confunda **isolado** com **errado** — uma posição isolada pode ser a melhor leitura; o que o usuário precisa saber é o risco de reforma que ela carrega.

Quando o usuário pediu **corroboração de um entendimento**, o risco é o viés de confirmação. Busque ativamente o contrário do que ele sustenta, e apresente os dois lados. Uma pesquisa que só encontra o que o usuário quer ouvir é uma pesquisa que falhou. Se o entendimento dele for minoritário, diga; se for contrário a tese vinculante, diga com clareza e antecedência.

## Quando não há julgado

Informe e pronto. "Não localizei julgados do TJSC sobre esta questão específica" é um resultado legítimo e útil. Registre a expressão de busca usada, para que o usuário possa avaliar se o recorte foi adequado.

Não preencha o vazio com precedente de matéria vizinha apresentado como se fosse do tema. Se um julgado de outra matéria for genuinamente útil por analogia, apresente-o **declarando** que é analogia.

## Transcrição das ementas

Transcreva a ementa **integral** de cada julgado citado, entre blockquote, e acompanhe de link para o inteiro teor. A transcrição literal é o que permite citar direto na decisão sem reabrir o portal.

Nunca reescreva, resuma dentro das aspas ou "limpe" a ementa. Se precisar cortar, marque o corte com colchetes.

Nunca invente julgado, número de processo, data ou URL. Se um precedente que você esperava encontrar não apareceu na busca, diga "não retornado nesta pesquisa" em vez de citá-lo de memória. Precedente citado sem fonte recuperada é alucinação, e numa decisão judicial o custo disso é alto.

Não complete a UF de origem quando o portal não a trouxer.

## Estrutura do relatório

Vale para o chat e para o PDF, com a diferença de que o PDF é o documento de arquivo.

1. **Questão pesquisada** — a pergunta, reformulada com precisão jurídica.
2. **Resposta direta** — dois ou três parágrafos com a conclusão. Quem lê só isso precisa sair sabendo.
3. **Precedentes qualificados** — vinculantes e de observância obrigatória, com tese literal. Se não houver, diga.
4. **Por tribunal** — TJSC, STJ, STF, cada julgado com identificação completa, ementa integral e link.
5. **Diálogo entre os tribunais** — a análise articulada.
6. **Alertas** — posição isolada, divergência interna, tese em revisão, julgado superado.
7. **Limites da pesquisa** — expressões usadas, bases consultadas, o que não foi coberto.

O item 7 não é formalidade. Registrar que a busca foi por ementa e não por inteiro teor, ou que 5.000 monocráticas ficaram de fora, é o que permite ao usuário calibrar a confiança no resultado.

## Identificação dos julgados

Formato: **Tribunal, classe e número, órgão julgador, relator, data de julgamento**. Para precedente qualificado, acrescente o tema e a situação.

```
TJSC, ApCiv 5001079-76.2024.8.24.0087, 4ª Câmara de Direito Público,
Rel. Des. Elleston Lissandro Canali, j. 27/08/2026

STJ, REsp 1.708.325/RS, Segunda Turma, Rel. Min. Og Fernandes, j. 24/05/2022

STF, RE 136861 (Tema 366), Tribunal Pleno, Rel. Min. Edson Fachin,
red. p/ acórdão Min. Alexandre de Moraes, j. 11/03/2020
```

## Cuidado com decisões que não julgaram o mérito

Agravo interno não conhecido, recurso barrado pela Súmula 7 do STJ, decisão que aplicou óbice de admissibilidade — **não** revelam o entendimento do tribunal sobre a matéria de fundo. É erro citá-los como "o STJ entende que X".

A Súmula 7 é especialmente traiçoeira: quando o STJ diz que rever a conclusão exigiria reexame de prova, ele está mantendo o acórdão local sem endossar sua tese. Se for citar, deixe claro o que a decisão realmente resolveu.
