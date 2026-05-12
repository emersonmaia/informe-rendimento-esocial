import axios from 'axios'

// Em dev o proxy do Vite encaminha /api → http://127.0.0.1:8080/api
const api = axios.create({ baseURL: '/api' })

export const getDashboard  = ()         => api.get('/dashboard')
export const getInformes   = ()         => api.get('/informes')
export const gerarInformes = ()         => api.post('/informes/gerar')
export const getJob        = (id)       => api.get(`/informes/jobs/${id}`)
export const verificarXmls = ()         => api.get('/importacao/verificar')
export const importarS1210 = ()         => api.post('/importacao/s1210')
export const importarS1200 = ()         => api.post('/importacao/s1200')
export const importarS2299 = ()         => api.post('/importacao/s2299')
export const importarTudo  = ()         => api.post('/importacao/tudo')
export const getJobImport  = (id)       => api.get(`/importacao/jobs/${id}`)
export const listarJobs    = ()         => api.get('/importacao/jobs')
export const limparDados   = ()         => api.delete('/importacao/dados')

// Configuração / multi-banco
export const getConexoes      = ()          => api.get('/config/conexoes')
export const ativarConexao    = (id)        => api.post(`/config/conexoes/ativar/${id}`)
export const adicionarConexao = (dados)     => api.post('/config/conexoes/novo', dados)
export const removerConexao   = (id)        => api.delete(`/config/conexoes/${id}`)
export const testarConexao    = (id)        => api.get(`/config/conexoes/testar/${id}`)
export const atualizarConexao = (id, dados) => api.put(`/config/conexoes/${id}`, dados)

export const pdfUrl = (codEmpresa, cpf) =>
  `/api/informes/pdf/${codEmpresa}/${cpf}`

export const getConferencia      = ()           => api.get('/conferencia')
export const getConferenciaMes   = (cpf)        => api.get(`/conferencia/por_mes/${cpf}`)
export const getConferenciaFolha           = (ano, mes) => api.get(`/conferencia-folha?ano=${ano}&mes=${mes}`)
export const getConferenciaFolhaFuncs      = (ano)      => api.get(`/conferencia-folha/funcionarios?ano=${ano}`)
export const getConferenciaFolhaPorFunc    = (cpf, ano) => api.get(`/conferencia-folha/por-funcionario/${cpf}?ano=${ano}`)
export const getPendenciasEsocial = (ano)        => api.get(`/pendencias-esocial?ano=${ano}`)
export const getIrpfTotais       = (cpf)        => api.get(`/irpf/totais/${cpf}`)

// Nomes override (beneficiarios nao identificados em FOLFUN)
export const getNomesOverride    = ()           => api.get('/nomes')
export const salvarNomeOverride  = (dados)      => api.post('/nomes', dados)
export const removerNomeOverride = (cpf)        => api.delete(`/nomes/${cpf}`)
export const getAjustesManuais   = ()           => api.get('/ajustes-manuais')
export const salvarAjusteManual  = (dados)      => api.post('/ajustes-manuais', dados)
export const removerAjusteManual = (id)         => api.delete(`/ajustes-manuais/${id}`)

export const excluirLinha    = (dados) => api.post('/excluir', dados)
export const restaurarLinha  = (id)   => api.delete(`/excluir/${id}`)
export const getExclusoesLinha = (cpf) => api.get(`/excluir/${cpf}`)

export default api
