import { useEffect, useState } from 'react'
import {
  Button, Card, Table, Tag, Typography, Space, Tooltip,
  Alert, Input, Modal, Spin, message,
} from 'antd'
import {
  CheckCircleOutlined, WarningOutlined, ReloadOutlined, CalendarOutlined,
  StopOutlined, UndoOutlined,
} from '@ant-design/icons'
import { getConferencia, getConferenciaMes, excluirLinha, restaurarLinha } from '../api'

const { Title, Text, Paragraph } = Typography
const { Search } = Input

const FS = { fontSize: 11 }
const MONO = { fontSize: 11, fontFamily: 'monospace' }

const fmt = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtCpf = (cpf) => {
  const c = (cpf || '').replace(/\D/g, '')
  return c.length === 11
    ? `${c.slice(0,3)}.${c.slice(3,6)}.${c.slice(6,9)}-${c.slice(9)}`
    : cpf
}

const ORIGEM_COLOR = { S1210: 'blue', S5001: 'cyan', S1200: 'purple', S2299: 'orange', MANUAL: 'green' }

function ModalPorMes({ cpf, nome, open, onClose, onRefresh }) {
  const [dados, setDados] = useState([])
  const [loading, setLoading] = useState(false)
  const [toggling, setToggling] = useState(null)

  const carregar = () => {
    if (!cpf) return
    setLoading(true)
    getConferenciaMes(cpf)
      .then(r => setDados(r.data))
      .catch(() => message.error('Erro ao carregar lançamentos'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { if (open && cpf) carregar() }, [open, cpf])

  const handleToggle = async (row) => {
    setToggling(row.row_id)
    try {
      if (row.excluido) {
        await restaurarLinha(row.excluir_id)
      } else {
        await excluirLinha({ tabela: row.tabela, row_id: row.row_id, cpf })
      }
      await carregar()
      onRefresh?.()
    } catch {
      message.error('Erro ao alterar exclusão')
    } finally {
      setToggling(null)
    }
  }

  const ativo = dados.filter(r => !r.excluido)

  const colunas = [
    { title: '', key: 'toggle', width: 36, align: 'center',
      render: (_, r) => {
        if (r.tabela === 'MANUAL') return null
        return (
          <Tooltip title={r.excluido ? 'Restaurar na soma' : 'Excluir da soma'}>
            <Button
              type="text" size="small"
              loading={toggling === r.row_id}
              icon={r.excluido
                ? <UndoOutlined style={{ color: '#52c41a', fontSize: 12 }} />
                : <StopOutlined style={{ color: '#cf1322', fontSize: 12 }} />}
              onClick={() => handleToggle(r)}
              style={{ padding: '0 4px' }}
            />
          </Tooltip>
        )
      },
    },
    { title: 'Competência', dataIndex: 'competencia', key: 'comp', width: 95,
      render: (v, r) => <Text style={{ ...FS, opacity: r.excluido ? 0.4 : 1 }}>{v}</Text> },
    { title: 'Dt Pagto', dataIndex: 'dt_pagto', key: 'pagto', width: 95,
      render: (v, r) => <Text style={{ ...FS, opacity: r.excluido ? 0.4 : 1 }}>{v?.slice(0,10)}</Text> },
    { title: 'Origem', dataIndex: 'origem', key: 'orig', width: 72,
      render: (o, r) => (
        <Tag color={r.excluido ? 'default' : (ORIGEM_COLOR[o] || 'default')}
          style={{ fontSize: 10, padding: '0 4px', opacity: r.excluido ? 0.4 : 1 }}>{o}</Tag>
      ),
    },
    { title: 'Rend. Trib.', dataIndex: 'rend_trib', key: 'rt', align: 'right',
      render: (v, r) => {
        const sup = !r.excluido && r.rend_trib_13 > 0
        return sup
          ? <Tooltip title="Zerado na soma — linha com 13º salário"><Text style={{ ...MONO, opacity: 0.35, textDecoration: 'line-through' }}>R$ {fmt(v)}</Text></Tooltip>
          : <Text style={{ ...MONO, opacity: r.excluido ? 0.4 : 1 }}>R$ {fmt(v)}</Text>
      } },
    { title: 'INSS', dataIndex: 'inss', key: 'inss', align: 'right',
      render: (v, r) => {
        const sup = !r.excluido && r.rend_trib_13 > 0
        return sup
          ? <Tooltip title="Zerado na soma — linha com 13º salário"><Text style={{ ...MONO, opacity: 0.35, textDecoration: 'line-through' }}>R$ {fmt(v)}</Text></Tooltip>
          : <Text style={{ ...MONO, opacity: r.excluido ? 0.4 : 1 }}>R$ {fmt(v)}</Text>
      } },
    { title: 'IRRF', dataIndex: 'irrf', key: 'irrf', align: 'right',
      render: (v, r) => {
        const sup = !r.excluido && r.rend_trib_13 > 0
        return sup
          ? <Tooltip title="Zerado na soma — linha com 13º salário"><Text style={{ ...MONO, opacity: 0.35, textDecoration: 'line-through', color: '#cf1322' }}>R$ {fmt(v)}</Text></Tooltip>
          : <Text style={{ ...MONO, color: r.excluido ? undefined : '#cf1322', opacity: r.excluido ? 0.4 : 1 }}>R$ {fmt(v)}</Text>
      } },
    { title: '13º Bruto', dataIndex: 'rend_trib_13', key: 'r13', align: 'right',
      render: (v, r) => v > 0
        ? <Text style={{ ...MONO, opacity: r.excluido ? 0.4 : 1 }}>R$ {fmt(v)}</Text>
        : <Text type="secondary" style={FS}>—</Text> },
    { title: 'INSS 13°', dataIndex: 'inss_13', key: 'inss13', align: 'right',
      render: (v, r) => v > 0
        ? <Text style={{ ...MONO, opacity: r.excluido ? 0.4 : 1 }}>R$ {fmt(v)}</Text>
        : <Text type="secondary" style={FS}>—</Text> },
    { title: 'IRRF 13°', dataIndex: 'irrf_13', key: 'irrf13', align: 'right',
      render: (v, r) => v > 0
        ? <Text style={{ ...MONO, color: r.excluido ? undefined : '#cf1322', opacity: r.excluido ? 0.4 : 1 }}>R$ {fmt(v)}</Text>
        : <Text type="secondary" style={FS}>—</Text> },
  ]

  return (
    <Modal
      open={open} onCancel={onClose}
      title={`Lançamentos — ${nome} (${fmtCpf(cpf)})`}
      footer={null} width={1050}
    >
      {loading
        ? <Spin style={{ display: 'block', margin: '24px auto' }} />
        : <Table
            dataSource={dados} columns={colunas} rowKey={(_, i) => i}
            size="small" pagination={false}
            rowClassName={r => r.excluido ? 'row-excluida' : ''}
            summary={() => {
              const sup  = r => r.rend_trib_13 > 0
              const tr   = ativo.reduce((s, r) => s + (sup(r) ? 0 : r.rend_trib), 0)
              const ins  = ativo.reduce((s, r) => s + (sup(r) ? 0 : r.inss), 0)
              const ir   = ativo.reduce((s, r) => s + (sup(r) ? 0 : r.irrf), 0)
              const r13  = ativo.reduce((s, r) => s + r.rend_trib_13, 0)
              const i13  = ativo.reduce((s, r) => s + (r.inss_13 || 0), 0)
              const ir13 = ativo.reduce((s, r) => s + (r.irrf_13 || 0), 0)
              const excl = dados.filter(r => r.excluido).length
              return (
                <Table.Summary.Row style={{ fontWeight: 600, background: '#fafafa' }}>
                  <Table.Summary.Cell index={0} colSpan={4}>
                    Total{excl > 0 && <Text type="secondary" style={{ fontSize: 10, marginLeft: 6 }}>({excl} excluído{excl > 1 ? 's' : ''})</Text>}
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={4} align="right"><Text style={MONO}>R$ {fmt(tr)}</Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={5} align="right"><Text style={MONO}>R$ {fmt(ins)}</Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={6} align="right"><Text style={{ ...MONO, color: '#cf1322' }}>R$ {fmt(ir)}</Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={7} align="right"><Text style={MONO}>R$ {fmt(r13)}</Text></Table.Summary.Cell>
                  <Table.Summary.Cell index={8} align="right">{i13 > 0 && <Text style={MONO}>R$ {fmt(i13)}</Text>}</Table.Summary.Cell>
                  <Table.Summary.Cell index={9} align="right">{ir13 > 0 && <Text style={{ ...MONO, color: '#cf1322' }}>R$ {fmt(ir13)}</Text>}</Table.Summary.Cell>
                </Table.Summary.Row>
              )
            }}
          />
      }
    </Modal>
  )
}

export default function Conferencia() {
  const [dados, setDados]         = useState([])
  const [filtrado, setFiltrado]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [erro, setErro]           = useState(null)
  const [filtro, setFiltro]       = useState('todos')
  const [busca, setBusca]         = useState('')
  const [modalCpf, setModalCpf]   = useState(null)
  const [modalNome, setModalNome] = useState('')

  const carregar = () => {
    setLoading(true)
    setErro(null)
    getConferencia()
      .then(r => { setDados(r.data); aplicarFiltros(r.data, filtro, busca) })
      .catch(e => setErro(e.response?.data?.detail || 'Erro ao carregar dados'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { carregar() }, [])

  const aplicarFiltros = (base, f, q) => {
    let arr = base
    if (f === 'nao_id') arr = arr.filter(r => !r.identificado)
    if (f === 'ok')     arr = arr.filter(r => r.identificado)
    if (q) {
      const lq = q.toLowerCase()
      arr = arr.filter(r =>
        r.nome.toLowerCase().includes(lq) ||
        r.cpf.includes(lq) ||
        (r.empresa || '').toLowerCase().includes(lq)
      )
    }
    setFiltrado(arr)
  }

  const handleFiltro = (f) => { setFiltro(f); aplicarFiltros(dados, f, busca) }
  const handleBusca  = (q) => { setBusca(q);  aplicarFiltros(dados, filtro, q) }

  const abrirMes = (r) => { setModalCpf(r.cpf); setModalNome(r.nome) }

  const naoId = dados.filter(r => !r.identificado).length

  const colunas = [
    {
      title: '',
      key: 'status',
      width: 70,
      align: 'center',
      render: (_, r) => (
        <Space size={6}>
          <Tooltip title={r.identificado ? `Identificado — ${r.empresa || ''}` : 'Não identificado'}>
            {r.identificado
              ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
              : <WarningOutlined     style={{ color: '#cf1322', fontSize: 14 }} />
            }
          </Tooltip>
          <Tooltip title="Ver por mês">
            <Button
              size="small"
              type="text"
              icon={<CalendarOutlined />}
              style={{ padding: '0 4px', color: '#1677ff' }}
              onClick={() => abrirMes(r)}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Nome',
      dataIndex: 'nome',
      key: 'nome',
      ellipsis: true,
      width: 220,
      sorter: (a, b) => a.nome.localeCompare(b.nome),
      render: (nome, r) => (
        <Text style={{ ...FS, color: r.identificado ? undefined : '#cf1322' }}>{nome}</Text>
      ),
    },
    {
      title: 'CPF',
      dataIndex: 'cpf',
      key: 'cpf',
      width: 125,
      render: v => <Text style={FS}>{fmtCpf(v)}</Text>,
    },
    {
      title: 'Ev.',
      dataIndex: 'qtd_eventos',
      key: 'qtd',
      width: 50,
      align: 'center',
      sorter: (a, b) => a.qtd_eventos - b.qtd_eventos,
      render: v => <Text style={FS}>{v}</Text>,
    },
    {
      title: 'Rend. Trib.',
      dataIndex: 'rend_trib',
      key: 'rt',
      width: 125,
      align: 'right',
      sorter: (a, b) => a.rend_trib - b.rend_trib,
      render: v => <Text style={MONO}>R$ {fmt(v)}</Text>,
    },
    {
      title: 'INSS',
      dataIndex: 'inss',
      key: 'inss',
      width: 105,
      align: 'right',
      render: v => <Text style={MONO}>R$ {fmt(v)}</Text>,
    },
    {
      title: 'IRRF',
      dataIndex: 'irrf',
      key: 'irrf',
      width: 105,
      align: 'right',
      render: v => <Text style={{ ...MONO, color: '#cf1322' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: '13º Líquido',
      dataIndex: 'decimo_terceiro_liquido',
      key: 'dec13',
      width: 110,
      align: 'right',
      render: v => v > 0
        ? <Text style={{ ...MONO, color: '#389e0d' }}>R$ {fmt(v)}</Text>
        : <Text type="secondary" style={FS}>—</Text>,
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>Conferência — Beneficiários eSocial {new Date().getFullYear() - 1}</Title>
      <Paragraph type="secondary">
        Lista todos os CPFs com dados no eSocial e verifica se estão identificados no cadastro de funcionários (FOLFUN).
      </Paragraph>

      {naoId > 0 && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message={`${naoId} CPF${naoId > 1 ? 's' : ''} não identificado${naoId > 1 ? 's' : ''} no cadastro`}
          description="Estes beneficiários aparecerão como 'NAO IDENTIFICADO' no informe. Verifique se o CPF está correto no FOLFUN."
          style={{ marginBottom: 16 }}
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button
            size="small"
            type={filtro === 'todos' ? 'primary' : 'default'}
            onClick={() => handleFiltro('todos')}
          >
            Todos ({dados.length})
          </Button>
          <Button
            size="small"
            type={filtro === 'ok' ? 'primary' : 'default'}
            onClick={() => handleFiltro('ok')}
          >
            Identificados ({dados.length - naoId})
          </Button>
          <Button
            size="small"
            type={filtro === 'nao_id' ? 'primary' : 'default'}
            danger={naoId > 0}
            onClick={() => handleFiltro('nao_id')}
          >
            Não identificados ({naoId})
          </Button>
          <Search
            placeholder="Buscar nome, CPF ou empresa"
            onSearch={handleBusca}
            onChange={e => handleBusca(e.target.value)}
            style={{ width: 240 }}
            size="small"
            allowClear
          />
          <Button size="small" icon={<ReloadOutlined />} onClick={carregar} loading={loading}>
            Atualizar
          </Button>
        </Space>
      </Card>

      {erro && <Alert type="error" message={erro} style={{ marginBottom: 16 }} showIcon />}

      <Card>
        <Table
          dataSource={filtrado}
          columns={colunas}
          rowKey="cpf"
          loading={loading}
          size="small"
          style={{ fontSize: 11 }}
          pagination={{ pageSize: 30, showSizeChanger: true }}
          scroll={{ x: 900 }}
          rowClassName={(r) => r.identificado ? '' : 'row-nao-identificado'}
          summary={(pageData) => {
            const tr  = pageData.reduce((s, r) => s + r.rend_trib, 0)
            const ins = pageData.reduce((s, r) => s + r.inss, 0)
            const ir  = pageData.reduce((s, r) => s + r.irrf, 0)
            return (
              <Table.Summary.Row style={{ fontWeight: 600, background: '#fafafa' }}>
                <Table.Summary.Cell index={0} colSpan={4}>Total da página</Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">
                  <Text style={MONO}>R$ {fmt(tr)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  <Text style={MONO}>R$ {fmt(ins)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={6} align="right">
                  <Text style={{ ...MONO, color: '#cf1322' }}>R$ {fmt(ir)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={7} />
              </Table.Summary.Row>
            )
          }}
        />
      </Card>

      <ModalPorMes
        cpf={modalCpf}
        nome={modalNome}
        open={!!modalCpf}
        onClose={() => setModalCpf(null)}
        onRefresh={carregar}
      />
    </div>
  )
}
