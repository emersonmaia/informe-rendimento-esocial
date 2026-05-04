import { useEffect, useState } from 'react'
import {
  Button, Card, Table, Tag, Typography, Space,
  Alert, Input, Row, Col, Statistic, DatePicker, Tooltip,
} from 'antd'
import {
  CheckCircleOutlined, WarningOutlined, CloseCircleOutlined,
  ReloadOutlined, QuestionCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { getConferenciaFolha } from '../api'

const { Title, Text } = Typography
const { Search } = Input

const fmt = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtCpf = (cpf) => {
  const c = (cpf || '').replace(/\D/g, '')
  return c.length === 11
    ? `${c.slice(0,3)}.${c.slice(3,6)}.${c.slice(6,9)}-${c.slice(9)}`
    : cpf
}

const fmtDif = (v) => {
  const n = Number(v || 0)
  if (Math.abs(n) < 0.05) return <Text type="secondary">—</Text>
  return (
    <Text style={{ fontFamily: 'monospace', color: n > 0 ? '#cf1322' : '#1677ff' }}>
      {n > 0 ? '+' : ''}{fmt(n)}
    </Text>
  )
}

const statusTag = (s) => {
  if (s === 'OK')
    return <Tag icon={<CheckCircleOutlined />} color="success">OK</Tag>
  if (s === 'DIVERGENTE')
    return <Tag icon={<WarningOutlined />} color="error">Divergente</Tag>
  return <Tag icon={<CloseCircleOutlined />} color="warning">Sem eSocial</Tag>
}

const corLinha = (r) => {
  if (r.status === 'DIVERGENTE')  return 'row-divergente'
  if (r.status === 'SEM_ESOCIAL') return 'row-sem-esocial'
  return ''
}

export default function ConferenciaFolha() {
  // Default: pagamento do mês anterior ao atual
  const hoje = dayjs()
  const [periodo, setPeriodo] = useState(hoje.subtract(1, 'month'))
  const [dados, setDados]     = useState([])
  const [filtrado, setFiltrado] = useState([])
  const [loading, setLoading]   = useState(false)
  const [erro, setErro]         = useState(null)
  const [filtro, setFiltro]     = useState('todos')
  const [busca, setBusca]       = useState('')

  const carregar = (p) => {
    const target = p || periodo
    setLoading(true)
    setErro(null)
    getConferenciaFolha(target.year(), target.month() + 1)
      .then(r => {
        setDados(r.data)
        aplicarFiltros(r.data, filtro, busca)
      })
      .catch(e => setErro(e.response?.data?.detail || 'Erro ao carregar dados'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [])

  const aplicarFiltros = (base, f, q) => {
    let arr = base
    if (f === 'ok')          arr = arr.filter(r => r.status === 'OK')
    if (f === 'divergente')  arr = arr.filter(r => r.status === 'DIVERGENTE')
    if (f === 'sem_esocial') arr = arr.filter(r => r.status === 'SEM_ESOCIAL')
    if (q) {
      const lq = q.toLowerCase()
      arr = arr.filter(r =>
        r.nome.toLowerCase().includes(lq) ||
        r.cpf.includes(lq.replace(/\D/g,''))
      )
    }
    setFiltrado(arr)
  }

  const handleFiltro = (f) => { setFiltro(f); aplicarFiltros(dados, f, busca) }
  const handleBusca  = (q) => { setBusca(q);  aplicarFiltros(dados, filtro, q) }

  const handleMes = (v) => {
    setPeriodo(v)
    setFiltro('todos')
    setBusca('')
    carregar(v)
  }

  const nOk          = dados.filter(r => r.status === 'OK').length
  const nDiv         = dados.filter(r => r.status === 'DIVERGENTE').length
  const nSemEsocial  = dados.filter(r => r.status === 'SEM_ESOCIAL').length

  const mesComp = periodo.subtract(1, 'month')
  const labelPgto = periodo.format('MM/YYYY')
  const labelComp = mesComp.format('MM/YYYY')

  const colunas = [
    {
      title: 'Status', key: 'status', width: 120, align: 'center', fixed: 'left',
      render: (_, r) => statusTag(r.status),
      filters: [
        { text: 'OK',           value: 'OK' },
        { text: 'Divergente',   value: 'DIVERGENTE' },
        { text: 'Sem eSocial',  value: 'SEM_ESOCIAL' },
      ],
      onFilter: (v, r) => r.status === v,
    },
    {
      title: 'Nome', dataIndex: 'nome', key: 'nome', ellipsis: true, width: 220,
      sorter: (a, b) => a.nome.localeCompare(b.nome),
    },
    { title: 'CPF', dataIndex: 'cpf', key: 'cpf', width: 140, render: fmtCpf },
    {
      title: 'Competência', key: 'comp', width: 110, align: 'center',
      render: (_, r) => `${r.ano_comp}-${String(r.mes_comp).padStart(2,'0')}`,
    },
    {
      title: 'Dt Pagto', dataIndex: 'data_pgto', key: 'pgto', width: 105, align: 'center',
    },
    {
      title: <Tooltip title="INSS na folha de pagamento">Folha INSS</Tooltip>,
      dataIndex: 'folha_inss', key: 'fi', width: 110, align: 'right',
      sorter: (a, b) => a.folha_inss - b.folha_inss,
      render: v => <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: <Tooltip title="INSS retornado pelo eSocial (S-5002)">eSocial INSS</Tooltip>,
      dataIndex: 'es_inss', key: 'ei', width: 110, align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: 'Dif INSS', dataIndex: 'dif_inss', key: 'di', width: 100, align: 'right',
      sorter: (a, b) => Math.abs(b.dif_inss) - Math.abs(a.dif_inss),
      render: fmtDif,
    },
    {
      title: <Tooltip title="IRRF na folha de pagamento">Folha IRRF</Tooltip>,
      dataIndex: 'folha_irrf', key: 'fr', width: 110, align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: <Tooltip title="IRRF retornado pelo eSocial (S-5002)">eSocial IRRF</Tooltip>,
      dataIndex: 'es_irrf', key: 'er', width: 110, align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: 'Dif IRRF', dataIndex: 'dif_irrf', key: 'dr', width: 100, align: 'right',
      sorter: (a, b) => Math.abs(b.dif_irrf) - Math.abs(a.dif_irrf),
      render: fmtDif,
    },
    {
      title: 'Líquido Folha', dataIndex: 'folha_liquido', key: 'liq', width: 120, align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace', color: '#389e0d' }}>R$ {fmt(v)}</Text>,
    },
  ]

  const totalFolhaInss = filtrado.reduce((s, r) => s + r.folha_inss, 0)
  const totalEsInss    = filtrado.reduce((s, r) => s + r.es_inss, 0)
  const totalFolhaIrrf = filtrado.reduce((s, r) => s + r.folha_irrf, 0)
  const totalEsIrrf    = filtrado.reduce((s, r) => s + r.es_irrf, 0)

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 4 }}>
        Conferência Folha vs eSocial — Pagamentos {labelPgto}
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        Competência <b>{labelComp}</b> · Compara INSS e IRRF da folha (FOLTOT/FOLEVE)
        com o retorno do eSocial (S-5002).
      </Text>

      {/* Resumo */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="Total" value={dados.length} valueStyle={{ fontSize: 22 }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderColor: '#b7eb8f' }}>
            <Statistic
              title="OK" value={nOk}
              valueStyle={{ color: '#389e0d', fontSize: 22 }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderColor: '#ffa39e' }}>
            <Statistic
              title="Divergentes" value={nDiv}
              valueStyle={{ color: '#cf1322', fontSize: 22 }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" style={{ borderColor: '#ffe58f' }}>
            <Statistic
              title="Sem eSocial" value={nSemEsocial}
              valueStyle={{ color: '#d4b106', fontSize: 22 }}
              prefix={<QuestionCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Alertas */}
      {nDiv > 0 && (
        <Alert type="error" showIcon icon={<WarningOutlined />}
          message={`${nDiv} pessoa${nDiv > 1 ? 's' : ''} com divergência de INSS ou IRRF`}
          description="Verifique se houve recolhimento incorreto ou evento de retificação pendente."
          style={{ marginBottom: 12 }}
        />
      )}
      {nSemEsocial > 0 && (
        <Alert type="warning" showIcon icon={<QuestionCircleOutlined />}
          message={`${nSemEsocial} pessoa${nSemEsocial > 1 ? 's' : ''} sem retorno do eSocial (S-5002)`}
          description="O S-5002 pode ainda não ter sido gerado, ou o XML não foi importado."
          style={{ marginBottom: 12 }}
        />
      )}

      {/* Filtros */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <DatePicker
            picker="month" value={periodo}
            onChange={handleMes}
            format="MM/YYYY"
            allowClear={false}
            placeholder="Mês de pagamento"
          />
          <Button
            type={filtro === 'todos'       ? 'primary' : 'default'}
            onClick={() => handleFiltro('todos')}
          >Todos ({dados.length})</Button>
          <Button
            type={filtro === 'ok'          ? 'primary' : 'default'}
            onClick={() => handleFiltro('ok')}
          >OK ({nOk})</Button>
          <Button
            type={filtro === 'divergente'  ? 'primary' : 'default'}
            danger={nDiv > 0}
            onClick={() => handleFiltro('divergente')}
          >Divergentes ({nDiv})</Button>
          <Button
            type={filtro === 'sem_esocial' ? 'primary' : 'default'}
            onClick={() => handleFiltro('sem_esocial')}
          >Sem eSocial ({nSemEsocial})</Button>
          <Search
            placeholder="Buscar nome ou CPF"
            onSearch={handleBusca}
            onChange={e => handleBusca(e.target.value)}
            style={{ width: 220 }}
            allowClear
            value={busca}
          />
          <Button icon={<ReloadOutlined />} onClick={() => carregar()} loading={loading}>
            Atualizar
          </Button>
        </Space>
      </Card>

      {erro && <Alert type="error" message={erro} style={{ marginBottom: 12 }} showIcon />}

      {/* Tabela */}
      <Card>
        <Table
          dataSource={filtrado}
          columns={colunas}
          rowKey="cpf"
          loading={loading}
          size="small"
          pagination={{ pageSize: 30, showSizeChanger: true, showTotal: (t) => `${t} registros` }}
          scroll={{ x: 1300 }}
          rowClassName={corLinha}
          summary={() => (
            <Table.Summary.Row style={{ fontWeight: 600, background: '#fafafa' }}>
              <Table.Summary.Cell index={0} colSpan={5}>Total da página</Table.Summary.Cell>
              <Table.Summary.Cell index={5} align="right">
                <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(totalFolhaInss)}</Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={6} align="right">
                <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(totalEsInss)}</Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={7} align="right">
                {fmtDif(totalFolhaInss - totalEsInss)}
              </Table.Summary.Cell>
              <Table.Summary.Cell index={8} align="right">
                <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(totalFolhaIrrf)}</Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={9} align="right">
                <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(totalEsIrrf)}</Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={10} align="right">
                {fmtDif(totalFolhaIrrf - totalEsIrrf)}
              </Table.Summary.Cell>
              <Table.Summary.Cell index={11} />
            </Table.Summary.Row>
          )}
        />
      </Card>

      <style>{`
        .row-divergente  td { background: #fff1f0 !important; }
        .row-sem-esocial td { background: #fffbe6 !important; }
      `}</style>
    </div>
  )
}
