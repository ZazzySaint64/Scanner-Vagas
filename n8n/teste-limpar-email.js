// Teste do código do nó "Limpa o e-mail". Roda com: node n8n/teste-limpar-email.js
// Imita o $input do n8n e confere a saída.
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const codigo = fs.readFileSync(path.join(__dirname, 'limpar-email.js'), 'utf8');
const rodar = emails => new Function('$input', codigo)({ all: () => emails.map(json => ({ json })) });

const html = `<html><head><style>p{color:red}</style></head><body>
  <p>Desenvolvedor(a) Full Stack Júnior &amp; Estágio</p>
  <div>Empresa Exemplo · Porto Alegre · Híbrido</div>
  <a href="https://vagas.exemplo.com/123?utm=abc&amp;x=1">Ver vaga</a>
  <p>Requisitos: React, Node.js, PostgreSQL e vontade de aprender.</p>
  <p>Para cancelar a inscrição clique aqui</p></body></html>`;

const saida = rodar([
  { subject: 'Nova vaga: Full Stack Júnior', textHtml: html },
  { subject: 'curto', textPlain: 'oi' },  // menos de 50 caracteres: descartado
]);

assert.strictEqual(saida.length, 1, 'e-mail curto descartado');
const { texto, empresa, link } = saida[0].json;
assert.strictEqual(empresa, 'Nova vaga: Full Stack Júnior');
assert.strictEqual(link, 'https://vagas.exemplo.com/123?utm=abc&x=1', 'link tirado do href, sem aspas');
assert.ok(texto.includes('Full Stack Júnior & Estágio'), 'entidade &amp; decodificada');
assert.ok(texto.includes('Requisitos: React'), 'conteúdo mantido');
assert.ok(!/color:red|<p>|https?:/.test(texto), 'sem CSS, tags e links');
assert.ok(!/cancelar a inscri/i.test(texto), 'rodapé removido');
console.log('ok: limpeza de e-mail funciona');
