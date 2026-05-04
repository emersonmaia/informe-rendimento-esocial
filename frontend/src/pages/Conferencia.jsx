import { useEffect, useState } from 'react'
import {
  Button, Card, Table, Tag, Typography, Space,
  Alert, Input, Modal, Spin, Tabs,
} from 'antd'
import {
  CheckCircleOutlined, WarningOutlined, ReloadOutlined,
} from '@ant-design/icons'
import { getConferencia, getConferenciaMes } from '../api'

const { Title, Text, Paragraph } = Typography
const { Search } = Input

const fmt = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtCpf = (cpf) => {
  const c = (cpf || '').replace(/\D/g, '')
  return c.length === 11
    ? `${c.slice(0,3)}.${c.slice(3,6)}.${c.slice(6,9)}-${c.slice(9)}`
    : cpf
}

function ModalPorMes({ cpf, nome, open, onClose }) {
  const [dados, setDados] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !cpf) return
    setLoading(true)
    getConferenciaMes(cpf)
      .then(r => setDados(r.data))
      .finally(() => setLoading(false))
  }, [open, cpf])

  const colunas = [
    { title: 'Competência', dataIndex: 'competencia', key: 'comp', width: 110 },
    { title: 'Dt Pagto',    dataIndex: 'dt_pagto',    key: 'pagto', width: 110 },
    {
      title: 'Origem', dataIndex: 'origem', key: 'orig', width: 80,
      render: o => <Tag color={o === 'S1210' ? 'blue' : 'purple'}>{o}</Tag>,
    },
    {
      title: 'Rend. Trib.', dataIndex: 'rend_trib', key: 'rt', align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: 'INSS', dataIndex: 'inss', key: 'inss', align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: 'IRRF', dataIndex: 'irrf', key: 'irrf', align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: '13º Bruto', dataIndex: 'rend_trib_13', key: 'r13', align: 'right',
      render: v => v > 0 ? <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text> : <Text type="secondary">—</Text>,
    },
  ]

  return (
    <Modal
      open={open} onCancel={onClose}
      title={`Eventos por mês — ${nome} (${fmtCpf(cpf)})`}
      footer={null} width={800}
    >
      {loading
        ? <Spin style={{ display: 'block', margin: '24px auto' }} />
        : <Table
            dataSource={dados} columns={colunas} rowKey={(r, i) => i}
            size="small" pagination={false}
            summary={(pageData) => {
              const tr  = pageData.reduce((s, r) => s + r.rend_trib, 0)
              const ins = pageData.reduce((s, r) => s + r.inss, 0)
              const ir  = pageData.reduce((s, r) => s + r.irrf, 0)
              const r13 = pageData.reduce((s, r) => s + r.rend_trib_13, 0)
              return (
                <Table.Summary.Row style={{ fontWeight: 600, background: '#fafafa' }}>
                  <Table.Summary.Cell index={0} colSpan={3}>Total</Table.Summary.Cell>
                  <Table.Summary.Cell index={3} align="right">
                    <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(tr)}</Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={4} align="right">
                    <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(ins)}</Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={5} align="right">
                    <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(ir)}</Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={6} align="right">
                    <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(r13)}</Text>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              )
            }}
          />
      }
    </Modal>
  )
}

export default function Conferencia() {
  const [dados, setDados]       = useState([])
  const [filtrado, setFiltrado] = useState([])
  const [loading, setLoading]   = useState(true)
  const [erro, setErro]         = useState(null)
  const [filtro, setFiltro]     = useState('todos')  // 'todos' | 'nao_id' | 'ok'
  const [busca, setBusca]       = useState('')
  const [modalCpf, setModalCpf] = useState(null)
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
        r.empresa.toLowerCase().includes(lq)
      )
    }
    setFiltrado(arr)
  }

  const handleFiltro = (f) => { setFiltro(f); aplicarFiltros(dados, f, busca) }
  const handleBusca  = (q) => { setBusca(q);  aplicarFiltros(dados, filtro, q) }

  const naoId = dados.filter(r => !r.identificado).length

  const colunas = [
    {
      title: 'Status', key: 'status', width: 120, align: 'center',
      render: (_, r) => r.identificado
        ? <Tag icon={<CheckCircleOutlined />} color="success">Identificado</Tag>
        : <Tag icon={<WarningOutlined />}     color="error">Não identificado</Tag>,
    },
    {
      title: 'Nome', dataIndex: 'nome', key: 'nome', ellipsis: true, width: 200,
      sorter: (a, b) => a.nome.localeCompare(b.nome),
      render: (nome, r) => (
        <Text style={{ color: r.identificado ? undefined : '#cf1322' }}>{nome}</Text>
      ),
    },
    { title: 'CPF', dataIndex: 'cpf', key: 'cpf', width: 140, render: fmtCpf },
    { title: 'Empresa', dataIndex: 'empresa', key: 'empresa', ellipsis: true, width: 180 },
    {
      title: 'Qtd Ev.', dataIndex: 'qtd_eventos', key: 'qtd', width: 80, align: 'center',
      sorter: (a, b) => a.qtd_eventos - b.qtd_eventos,
    },
    {
      title: 'Rend. Trib.', dataIndex: 'rend_trib', key: 'rt', width: 130, align: 'right',
      sorter: (a, b) => a.rend_trib - b.rend_trib,
      render: v => <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: 'INSS', dataIndex: 'inss', key: 'inss', width: 110, align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: 'IRRF', dataIndex: 'irrf', key: 'irrf', width: 110, align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: '13º Líquido', dataIndex: 'decimo_terceiro_liquido', key: 'dec13', width: 120, align: 'right',
      render: v => v > 0
        ? <Text style={{ fontFamily: 'monospace', color: '#389e0d' }}>R$ {fmt(v)}</Text>
        : <Text type="secondary">—</Text>,
    },
    {
      title: '', key: 'detalhe', width: 90, align: 'center',
      render: (_, r) => (
        <Button size="small" onClick={() => { setModalCpf(r.cpf); setModalNome(r.nome) }}>
          Por mês
        </Button>
      ),
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
            type={filtro === 'todos'  ? 'primary' : 'default'}
            onClick={() => handleFiltro('todos')}
          >
            Todos ({dados.length})
          </Button>
          <Button
            type={filtro === 'ok'     ? 'primary' : 'default'}
            onClick={() => handleFiltro('ok')}
          >
            Identificados ({dados.length - naoId})
          </Button>
          <Button
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
            style={{ width: 260 }}
            allowClear
          />
          <Button icon={<ReloadOutlined />} onClick={carregar} loading={loading}>
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
          pagination={{ pageSize: 25, showSizeChanger: true }}
          scroll={{ x: 1100 }}
          rowClassName={(r) => r.identificado ? '' : 'row-nao-identificado'}
          summary={(pageData) => {
            const tr  = pageData.reduce((s, r) => s + r.rend_trib, 0)
            const ins = pageData.reduce((s, r) => s + r.inss, 0)
            const ir  = pageData.reduce((s, r) => s + r.irrf, 0)
            return (
              <Table.Summary.Row style={{ fontWeight: 600, background: '#fafafa' }}>
                <Table.Summary.Cell index={0} colSpan={5}>Total da página</Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(tr)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={6} align="right">
                  <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(ins)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={7} align="right">
                  <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(ir)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={8} colSpan={2} />
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
      />
    </div>
  )
}
