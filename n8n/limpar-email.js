// Código do nó Code "Limpa o e-mail" (fluxo 2). Já vem dentro do JSON do fluxo;
// este arquivo é a cópia legível e testável (fase4.bat, opção de teste).
//
// Entra: e-mails lidos pelo gatilho IMAP (campos subject, from, textPlain, textHtml).
// Sai: { texto, empresa, link } no formato que a rota /avaliar-vaga espera.
//
// ponytail: limpeza genérica. Um e-mail de alerta com 5 vagas vira UMA avaliação
// do e-mail inteiro. Separar vaga por vaga exige regras por site (LinkedIn, Gupy...).

function limpar(e) {
  const bruto = (e.textPlain || '') + '\n' + (e.textHtml || '');
  // O primeiro link costuma ser o da vaga. Pego ANTES de tirar as tags, senão o
  // href some junto. Para em aspas e < >, que delimitam o link dentro do HTML.
  const achado = bruto.match(/https?:\/\/[^\s"'<>]+/);
  const link = achado ? achado[0].replace(/&amp;/g, '&').slice(0, 500) : null;  // 500 = limite da rota

  let texto = e.textPlain || '';
  if (!texto.trim() && e.textHtml) {
    texto = e.textHtml
      .replace(/<(style|script|head)[\s\S]*?<\/\1>/gi, ' ')   // CSS e scripts não são texto
      .replace(/<br\s*\/?>|<\/(p|div|li|tr|h\d)>/gi, '\n')     // fim de bloco vira quebra de linha
      .replace(/<[^>]+>/g, ' ')                                // tira as outras tags
      .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'");
  }

  texto = texto
    .replace(/https?:\/\/\S+/g, ' ')  // links de rastreio são enormes e só gastam tokens
    .split('\n')
    .map(l => l.replace(/[ \t]+/g, ' ').trim())
    .filter(Boolean)
    // Rodapé de e-mail não diz nada sobre a vaga.
    .filter(l => !/descadastr|unsubscribe|cancelar (a )?inscri|privacidade|privacy|prefer[eê]ncias de e-?mail/i.test(l))
    .join('\n')
    .slice(0, 20000);  // mesmo limite da rota /avaliar-vaga

  // Sem nome de empresa confiável no e-mail: usa o assunto como rótulo.
  const empresa = (e.subject || 'alerta de vaga').toString().slice(0, 200);
  return { texto, empresa, link };
}

// O agente recusa texto com menos de 50 caracteres; e-mail vazio nem é enviado.
return $input.all()
  .map(item => ({ json: limpar(item.json) }))
  .filter(item => item.json.texto.length >= 50);
