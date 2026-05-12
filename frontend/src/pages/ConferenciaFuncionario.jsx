import { useEffect, useState } from 'react'
import {
  Card, Select, Typography, Space, Table, Tag, Alert,
  Spin, Row, Col, Statistic, Tooltip, Badge,
} from 'antd'
import {
  CheckCircleOutlined, WarningOutlined, QuestionCircleOutlined,
  CloseCircleOutlined, SendOutlined,
} from '@ant-design/icons'
import { getConferenciaFolhaFuncs, getConferenciaFolhaPorFunc } from '../api'

const { Title, Text } = Typography

const ANO = new Date().getFullYear() - 1

const fmt = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtCpf = (cpf) => {
  const c = (cpf || '').replace(/\D/g, '')
  return c.length === 11
    ? `${c.slice(0,3)}.${c.slice(3,6)}.${c.slice(6,9)}-${c.slice(9)}`
    : cpf
}

const Val = ({ v, color }) => (
  <Text style={{ fontFamily: 'monospace', color, fontSize: 12 }}>{fmt(v)}</Text>
)

const ValOpt = ({ v, color }) => {
  if (!v || Math.abs(Number(v)) < 0.005)
    return <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>—</Text>
  return <Val v={v} color={color} />
}

const Dif = ({ v }) => {
  const n = Number(v || 0)
  if (Math.abs(n) < 0.05)
    return <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>—</Text>
  return (
    <Text style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 12, color: n > 0 ? '#cf1322' : '#1677ff' }}>
      {n > 0 ? '+' : ''}{fmt(n)}
    </Text>
  )
}

const statusRow = (r) => {
  const hasFolha   = r.folha_inss > 0 || r.folha_irrf > 0 || r.folha_bruto > 0
  const hasEsocial = r.s1210_qtd > 0 || r.manual_qtd > 0
  if (Math.abs(r.dif_inss) > 0.05 || Math.abs(r.dif_irrf) > 0.05) return 'DIVERGENTE'
  if (hasFolha && !hasEsocial) return 'SEM_ESOCIAL'
  if (!hasFolha && hasEsocial) return 'SEM_FOLHA'
  return 'OK'
}

const StatusIcon = ({ s }) => {
  if (s === 'DIVERGENTE')
    return <Tooltip title="Divergência INSS ou IRRF"><WarningOutlined style={{ color: '#cf1322' }} /></Tooltip>
  if (s === 'SEM_ESOCIAL')
    return <Tooltip title="Folha sem retorno S1210"><QuestionCircleOutlined style={{ color: '#d4b106' }} /></Tooltip>
  if (s === 'SEM_FOLHA')
    return <Tooltip title="S1210 sem folha correspondente"><CloseCircleOutlined style={{ color: '#fa8c16' }} /></Tooltip>
  return <CheckCircleOutlined style={{ color: '#52c41a' }} />
}

const EnviadoIcon = ({ protocolo, nrrecibo }) => {
  if (!protocolo) return <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
  if (nrrecibo)
    return <Tooltip title={`Recibo: ${nrrecibo}`}><Tag color="green" style={{ fontSize: 10 }}>Confirmado</Tag></Tooltip>
  return <Tooltip title={`Protocolo: ${protocolo}`}><Tag color="blue" style={{ fontSize: 10 }}>Enviado</Tag></Tooltip>
}

export default function ConferenciaFuncionario() {
  const [funcs,    setFuncs]    = useState([])
  const [loadingF, setLoadingF] = useState(true)
  const [erroList, setErroList] = useState(null)
  const [cpfSel,   setCpfSel]   = useState(null)
  const [dados,    setDados]    = useState([])
  const [loading,  setLoading]  = useState(false)
  const [erro,     setErro]     = useState(null)

  useEffect(() => {
    getConferenciaFolhaFuncs(ANO)
      .then(r => setFuncs(r.data))
      .catch(e => setErroList(e.response?.data?.detail || 'Erro ao carregar funcionários'))
      .finally(() => setLoadingF(false))
  }, [])

  const handleSel = (cpf) => {
    setCpfSel(cpf)
    setDados([])
    setErro(null)
    setLoading(true)
    getConferenciaFolhaPorFunc(cpf, ANO)
      .then(r => setDados(r.data))
      .catch(e => setErro(e.response?.data?.detail || 'Erro ao carregar dados'))
      .finally(() => setLoading(false))
  }

  const funcSel  = funcs.find(f => f.cpf === cpfSel)
  const dadosExt = dados.map(r => ({ ...r, _status: statusRow(r) }))

  const nDiv    = dadosExt.filter(r => r._status === 'DIVERGENTE').length
  const nSemEs  = dadosExt.filter(r => r._status === 'SEM_ESOCIAL').length
  const nSemFol = dadosExt.filter(r => r._status === 'SEM_FOLHA').length

  const tot = (campo) => dados.reduce((s, r) => s + (r[campo] || 0), 0)

  const colunas = [
    {
      title: 'Comp.',
      dataIndex: 'competencia',
      key: 'comp',
      width: 78,
      align: 'center',
      fixed: 'left',
      render: v => <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '',
      key: 'status',
      width: 26,
      align: 'center',
      fixed: 'left',
      render: (_, r) => <StatusIcon s={r._status} />,
    },

    // ── FOLHA (FOLEVE × ES_S1200) ──────────────────────────────────────────
    {
      title: <span style={{ color: '#389e0d' }}>FOLHA (FOLEVE)</span>,
      children: [
        {
          title: <Tooltip title="Total créditos da folha (TCREDITO)">Bruto</Tooltip>,
          dataIndex: 'folha_bruto',     key: 'fb',   width: 100, align: 'right',
          render: v => <ValOpt v={v} />,
        },
        {
          title: <Tooltip title="Base de cálculo INSS (FOLEVE.BASE_INSS)">Base INSS</Tooltip>,
          dataIndex: 'folha_base_inss', key: 'fbi',  width: 100, align: 'right',
          render: v => <ValOpt v={v} />,
        },
        {
          title: 'INSS',
          dataIndex: 'folha_inss',      key: 'fi',   width: 88, align: 'right',
          render: v => <ValOpt v={v} color="#fa8c16" />,
        },
        {
          title: <Tooltip title="Base de cálculo IRRF (FOLEVE.BASE_IRRF)">Base IRRF</Tooltip>,
          dataIndex: 'folha_base_irrf', key: 'fbir', width: 100, align: 'right',
          render: v => <ValOpt v={v} />,
        },
        {
          title: 'IRRF',
          dataIndex: 'folha_irrf',      key: 'fr',   width: 88, align: 'right',
          render: v => <ValOpt v={v} color="#cf1322" />,
        },
        {
          title: 'Líquido',
          dataIndex: 'folha_liquido',   key: 'fl',   width: 100, align: 'right',
          render: v => <ValOpt v={v} color="#389e0d" />,
        },
        {
          title: 'FGTS',
          dataIndex: 'folha_fgts',      key: 'fgts', width: 88, align: 'right',
          render: v => <ValOpt v={v} />,
        },
        {
          title: <Tooltip title="Situação do envio ao eSocial (ES_S1200)">Enviado</Tooltip>,
          key: 'enviado', width: 90, align: 'center',
          render: (_, r) => <EnviadoIcon protocolo={r.es_protocolo} nrrecibo={r.es_nrrecibo} />,
        },
      ],
    },

    // ── S1210 IMPORTADO ────────────────────────────────────────────────────
    {
      title: <span style={{ color: '#1677ff' }}>S1210 Importado</span>,
      children: [
        {
          title: <Tooltip title="Rendimento tributável — heurística: rend13>0 → zera rend_trib">Rend Trib</Tooltip>,
          dataIndex: 's1210_rend_trib', key: 'sr',   width: 100, align: 'right',
          render: v => <ValOpt v={v} color="#1677ff" />,
        },
        {
          title: 'INSS',
          dataIndex: 's1210_inss',      key: 'si',   width: 88, align: 'right',
          render: v => <ValOpt v={v} color="#fa8c16" />,
        },
        {
          title: 'IRRF',
          dataIndex: 's1210_irrf',      key: 'sir',  width: 88, align: 'right',
          render: v => <ValOpt v={v} color="#cf1322" />,
        },
        {
          title: <Tooltip title="Rendimento tributável do 13º (REND_TRIB_13)">13º Rend</Tooltip>,
          dataIndex: 's1210_rend13',    key: 'sr13', width: 88, align: 'right',
          render: v => <ValOpt v={v} />,
        },
        {
          title: <Tooltip title="Quantidade de eventos S1210 importados">Qtd</Tooltip>,
          dataIndex: 's1210_qtd',       key: 'sq',   width: 50, align: 'center',
          render: v => v > 0
            ? <Tag color="blue"   style={{ margin: 0, fontSize: 11 }}>{v}</Tag>
            : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
        },
      ],
    },

    // ── AJUSTE MANUAL ──────────────────────────────────────────────────────
    {
      title: <span style={{ color: '#722ed1' }}>Ajuste Manual</span>,
      children: [
        {
          title: 'Rend Trib',
          dataIndex: 'manual_rend_trib', key: 'mr',  width: 100, align: 'right',
          render: v => <ValOpt v={v} color="#722ed1" />,
        },
        {
          title: 'INSS',
          dataIndex: 'manual_inss',      key: 'mi',  width: 88, align: 'right',
          render: v => <ValOpt v={v} color="#fa8c16" />,
        },
        {
          title: 'IRRF',
          dataIndex: 'manual_irrf',      key: 'mir', width: 88, align: 'right',
          render: v => <ValOpt v={v} color="#cf1322" />,
        },
        {
          title: 'Qtd',
          dataIndex: 'manual_qtd',       key: 'mq',  width: 50, align: 'center',
          render: v => v > 0
            ? <Tag color="purple" style={{ margin: 0, fontSize: 11 }}>{v}</Tag>
            : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
        },
      ],
    },

    // ── TOTAL PDF (S1210 + Manual) ─────────────────────────────────────────
    {
      title: <span style={{ color: '#08979c' }}>Total PDF (S1210 + Manual)</span>,
      children: [
        {
          title: 'Rend Trib',
          dataIndex: 'pdf_rend_trib', key: 'pr',   width: 100, align: 'right',
          render: v => <Val v={v} color="#08979c" />,
        },
        {
          title: 'INSS',
          dataIndex: 'pdf_inss',      key: 'pi',   width: 88, align: 'right',
          render: v => <Val v={v} color="#fa8c16" />,
        },
        {
          title: 'IRRF',
          dataIndex: 'pdf_irrf',      key: 'pir',  width: 88, align: 'right',
          render: v => <Val v={v} color="#cf1322" />,
        },
        {
          title: '13º Rend',
          dataIndex: 'pdf_rend13',    key: 'pr13', width: 88, align: 'right',
          render: v => <ValOpt v={v} />,
        },
        {
          title: '13º INSS',
          dataIndex: 'pdf_inss13',    key: 'pi13', width: 88, align: 'right',
          render: v => <ValOpt v={v} color="#fa8c16" />,
        },
        {
          title: '13º IRRF',
          dataIndex: 'pdf_irrf13',    key: 'pir13',width: 88, align: 'right',
          render: v => <ValOpt v={v} color="#cf1322" />,
        },
      ],
    },

    // ── DIFERENÇA (Folha − PDF) ────────────────────────────────────────────
    {
      title: 'Diferença (Folha − PDF)',
      children: [
        {
          title: 'INSS',
          dataIndex: 'dif_inss', key: 'di', width: 92, align: 'right',
          render: v => <Dif v={v} />,
        },
        {
          title: 'IRRF',
          dataIndex: 'dif_irrf', key: 'dr', width: 92, align: 'right',
          render: v => <Dif v={v} />,
        },
      ],
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 4 }}>
        Conferência por Funcionário — {ANO}
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        Compara por mês: <b>Folha (FOLEVE)</b> × <b>S1210 importado</b> × <b>Ajustes manuais</b> × <b>Total PDF</b>.
        Diferença = Folha − PDF. Positivo = folha maior; negativo = eSocial maior.
      </Text>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap align="center">
          <Text strong>Funcionário:</Text>
          {loadingF ? <Spin size="small" /> : (
            <Select
              showSearch
              placeholder="Selecione um funcionário"
              style={{ minWidth: 340 }}
              onChange={handleSel}
              value={cpfSel}
              filterOption={(inp, opt) => opt.label?.toLowerCase().includes(inp.toLowerCase())}
              options={funcs.map(f => ({
                value: f.cpf,
                label: f.nome ? `${f.nome} — ${fmtCpf(f.cpf)}` : fmtCpf(f.cpf),
              }))}
            />
          )}
          {funcSel && (
            <Text type="secondary">CPF {fmtCpf(cpfSel)}</Text>
          )}
        </Space>
      </Card>

      {erroList && (
        <Alert type="error" message={`Erro ao carregar funcionários: ${erroList}`} showIcon style={{ marginBottom: 12 }} />
      )}

      {cpfSel && loading && (
        <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
      )}

      {erro && (
        <Alert type="error" message={erro} showIcon style={{ marginBottom: 12 }} />
      )}

      {!loading && dados.length > 0 && (
        <>
          {/* Cards de resumo */}
          <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
            <Col xs={12} sm={4}>
              <Card size="small">
                <Statistic title="Meses" value={dados.length} valueStyle={{ fontSize: 18 }} />
              </Card>
            </Col>
            <Col xs={12} sm={4}>
              <Card size="small" style={nDiv > 0 ? { borderColor: '#ffa39e' } : {}}>
                <Statistic
                  title="Divergentes" value={nDiv}
                  valueStyle={{ color: nDiv > 0 ? '#cf1322' : undefined, fontSize: 18 }}
                  prefix={nDiv > 0 ? <WarningOutlined /> : null}
                />
              </Card>
            </Col>
            <Col xs={12} sm={4}>
              <Card size="small">
                <Statistic title="INSS Folha (ano)" value={`R$ ${fmt(tot('folha_inss'))}`} valueStyle={{ fontSize: 13, color: '#fa8c16' }} />
              </Card>
            </Col>
            <Col xs={12} sm={4}>
              <Card size="small">
                <Statistic title="INSS PDF (ano)" value={`R$ ${fmt(tot('pdf_inss'))}`} valueStyle={{ fontSize: 13, color: '#fa8c16' }} />
              </Card>
            </Col>
            <Col xs={12} sm={4}>
              <Card size="small">
                <Statistic title="Rend Trib PDF" value={`R$ ${fmt(tot('pdf_rend_trib'))}`} valueStyle={{ fontSize: 13, color: '#08979c' }} />
              </Card>
            </Col>
            <Col xs={12} sm={4}>
              <Card size="small">
                <Statistic title="13º PDF" value={`R$ ${fmt(tot('pdf_rend13'))}`} valueStyle={{ fontSize: 13 }} />
              </Card>
            </Col>
          </Row>

          {nDiv > 0 && (
            <Alert type="error" showIcon
              message={`${nDiv} mês${nDiv > 1 ? 'es' : ''} com divergência de INSS ou IRRF entre folha e PDF`}
              style={{ marginBottom: 8 }}
            />
          )}
          {nSemEs > 0 && (
            <Alert type="warning" showIcon
              message={`${nSemEs} mês${nSemEs > 1 ? 'es' : ''} com folha mas sem retorno S1210`}
              style={{ marginBottom: 8 }}
            />
          )}
          {nSemFol > 0 && (
            <Alert type="warning" showIcon
              message={`${nSemFol} mês${nSemFol > 1 ? 'es' : ''} com S1210 mas sem folha FOLEVE (ex.: rescisão)`}
              style={{ marginBottom: 8 }}
            />
          )}

          <Card bodyStyle={{ padding: 0 }}>
            <Table
              dataSource={dadosExt}
              columns={colunas}
              rowKey="competencia"
              size="small"
              pagination={false}
              scroll={{ x: 2600 }}
              bordered
              rowClassName={r =>
                r._status === 'DIVERGENTE'  ? 'row-divergente'  :
                r._status === 'SEM_ESOCIAL' ? 'row-sem-esocial' :
                r._status === 'SEM_FOLHA'   ? 'row-sem-folha'   : ''
              }
              summary={() => (
                <Table.Summary.Row style={{ fontWeight: 600, background: '#f0f5ff' }}>
                  <Table.Summary.Cell colSpan={2} align="center">
                    <Text strong style={{ fontSize: 11 }}>Total {ANO}</Text>
                  </Table.Summary.Cell>
                  {/* folha */}
                  <Table.Summary.Cell align="right"><Val v={tot('folha_bruto')} /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('folha_base_inss')} /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('folha_inss')} color="#fa8c16" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('folha_base_irrf')} /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('folha_irrf')} color="#cf1322" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('folha_liquido')} color="#389e0d" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('folha_fgts')} /></Table.Summary.Cell>
                  <Table.Summary.Cell />
                  {/* s1210 */}
                  <Table.Summary.Cell align="right"><Val v={tot('s1210_rend_trib')} color="#1677ff" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('s1210_inss')} color="#fa8c16" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('s1210_irrf')} color="#cf1322" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('s1210_rend13')} /></Table.Summary.Cell>
                  <Table.Summary.Cell />
                  {/* manual */}
                  <Table.Summary.Cell align="right"><Val v={tot('manual_rend_trib')} color="#722ed1" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('manual_inss')} color="#fa8c16" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('manual_irrf')} color="#cf1322" /></Table.Summary.Cell>
                  <Table.Summary.Cell />
                  {/* pdf */}
                  <Table.Summary.Cell align="right"><Val v={tot('pdf_rend_trib')} color="#08979c" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('pdf_inss')} color="#fa8c16" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('pdf_irrf')} color="#cf1322" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('pdf_rend13')} /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('pdf_inss13')} color="#fa8c16" /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Val v={tot('pdf_irrf13')} color="#cf1322" /></Table.Summary.Cell>
                  {/* dif */}
                  <Table.Summary.Cell align="right"><Dif v={tot('folha_inss') - tot('pdf_inss')} /></Table.Summary.Cell>
                  <Table.Summary.Cell align="right"><Dif v={tot('folha_irrf') - tot('pdf_irrf')} /></Table.Summary.Cell>
                </Table.Summary.Row>
              )}
            />
          </Card>
        </>
      )}

      {!cpfSel && !loading && (
        <Alert type="info" message="Selecione um funcionário para iniciar a conferência" showIcon />
      )}

      {!loading && cpfSel && dados.length === 0 && !erro && (
        <Alert type="warning" message="Nenhum dado encontrado para este funcionário no ano selecionado" showIcon />
      )}

      <style>{`
        .row-divergente  td { background: #fff1f0 !important; }
        .row-sem-esocial td { background: #fffbe6 !important; }
        .row-sem-folha   td { background: #fff7e6 !important; }
        .ant-table-thead > tr > th { font-size: 11px !important; padding: 4px 6px !important; }
        .ant-table-tbody > tr > td { padding: 3px 6px !important; }
      `}</style>
    </div>
  )
}
