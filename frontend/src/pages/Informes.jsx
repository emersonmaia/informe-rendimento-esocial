import { useState, useEffect, useRef } from 'react'
import {
  Button, Card, Table, Tag, Typography, Space, Divider, Tooltip,
  Input, Alert, Modal, Form, InputNumber, message, Popconfirm,
} from 'antd'
import {
  FilePdfOutlined, PrinterOutlined, SyncOutlined,
  ReloadOutlined, EyeOutlined, DownloadOutlined,
  EditOutlined, DeleteOutlined, PlusOutlined, CalendarOutlined,
  ClockCircleOutlined, StopOutlined, WarningOutlined, UndoOutlined,
} from '@ant-design/icons'
import {
  getInformes, gerarInformes, getJob, pdfUrl,
  getAjustesManuais, salvarAjusteManual, removerAjusteManual,
  getConferenciaMes, excluirLinha, restaurarLinha,
} from '../api'

const { Title, Text, Paragraph } = Typography
const { Search } = Input

const FS   = { fontSize: 11 }
const MONO = { fontSize: 11, fontFamily: 'monospace' }

const fmt = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtCpf = (cpf) => {
  const c = (cpf || '').replace(/\D/g, '')
  return c.length === 11
    ? `${c.slice(0, 3)}.${c.slice(3, 6)}.${c.slice(6, 9)}-${c.slice(9)}`
    : cpf
}

const ORIGEM_COLOR = {
  S1210: 'blue', S5001: 'cyan', S1200: 'purple', S2299: 'orange', MANUAL: 'green',
}

function AjustesManuaisModal({ open, onClose, onSaved, preloadRow }) {
  const [linhas,      setLinhas]      = useState([])
  const [carregando,  setCarregando]  = useState(false)
  const [formVisible, setFormVisible] = useState(false)
  const [editando,    setEditando]    = useState(null)
  const [salvando,    setSalvando]    = useState(false)
  const [toggling,    setToggling]    = useState(null)
  const [form] = Form.useForm()

  const isEmpMode = !!preloadRow

  const carregar = () => {
    setCarregando(true)
    if (isEmpMode) {
      getConferenciaMes(preloadRow.cpf)
        .then(r => setLinhas(r.data))
        .catch(() => setLinhas([]))
        .finally(() => setCarregando(false))
    } else {
      getAjustesManuais()
        .then(r => setLinhas(r.data.map(a => ({ ...a, manual_id: a.id, origem: 'MANUAL' }))))
        .catch(() => setLinhas([]))
        .finally(() => setCarregando(false))
    }
  }

  useEffect(() => {
    if (open) {
      carregar()
      setFormVisible(false)
      setEditando(null)
      form.resetFields()
    }
  }, [open, preloadRow])

  const abrirFormNovo = () => {
    setEditando(null)
    form.resetFields()
    if (isEmpMode) {
      form.setFieldsValue({
        cpf:     preloadRow.cpf,
        empresa: preloadRow.cod_empresa ? Number(preloadRow.cod_empresa) : undefined,
        rend_trib: 0, inss: 0, irrf: 0,
        rend_trib_13: 0, inss_13: 0, irrf_13: 0,
      })
    }
    setFormVisible(true)
  }

  const abrirFormEditar = (row) => {
    setEditando(row)
    form.setFieldsValue({
      cpf:          row.cpf ?? preloadRow?.cpf ?? '',
      empresa:      row.empresa ?? (preloadRow?.cod_empresa ? Number(preloadRow.cod_empresa) : undefined),
      competencia:  row.competencia,
      dt_pagto:     row.dt_pagto?.slice(0, 10),
      rend_trib:    row.rend_trib,
      inss:         row.inss,
      irrf:         row.irrf,
      rend_trib_13: row.rend_trib_13,
      inss_13:      row.inss_13,
      irrf_13:      row.irrf_13,
      cod_receita:  row.cod_receita || '',
      obs:          row.obs || '',
    })
    setFormVisible(true)
  }

  const handleSalvar = (vals) => {
    setSalvando(true)
    salvarAjusteManual({
      id:  editando?.manual_id ?? null,
      ...vals,
      cpf: (vals.cpf || '').replace(/\D/g, ''),
      cod_receita: vals.cod_receita || '',
      obs:         vals.obs || '',
    })
      .then(() => {
        message.success('Ajuste salvo')
        setFormVisible(false)
        setEditando(null)
        carregar()
        onSaved?.()
      })
      .catch(e => message.error(e.response?.data?.detail || 'Erro ao salvar'))
      .finally(() => setSalvando(false))
  }

  const handleToggle = async (row) => {
    setToggling(row.row_id)
    try {
      if (row.excluido) {
        await restaurarLinha(row.excluir_id)
      } else {
        await excluirLinha({ tabela: row.tabela, row_id: row.row_id, cpf: preloadRow.cpf })
      }
      await carregar()
      onSaved?.()
    } catch {
      message.error('Erro ao alterar exclusão')
    } finally {
      setToggling(null)
    }
  }

  const handleRemover = (manualId) => {
    removerAjusteManual(manualId)
      .then(() => {
        message.success('Removido')
        if (editando?.manual_id === manualId) { setFormVisible(false); setEditando(null) }
        carregar()
        onSaved?.()
      })
      .catch(e => message.error(e.response?.data?.detail || 'Erro ao remover'))
  }

  const colsBase = [
    { title: 'Comp.', dataIndex: 'competencia', width: 85,
      render: (v, r) => <Text style={{ ...FS, opacity: r.excluido ? 0.4 : 1 }}>{v}</Text> },
    { title: 'Dt Pgto', dataIndex: 'dt_pagto', width: 95,
      render: (v, r) => <Text style={{ ...FS, opacity: r.excluido ? 0.4 : 1 }}>{v?.slice(0, 10)}</Text> },
    { title: 'Rend. Trib.', dataIndex: 'rend_trib', width: 100, align: 'right',
      render: (v, r) => {
        const sup = !r.excluido && r.rend_trib_13 > 0
        return sup
          ? <Tooltip title="Zerado na soma — linha com 13º salário"><Text style={{ ...MONO, opacity: 0.35, textDecoration: 'line-through' }}>{fmt(v)}</Text></Tooltip>
          : <Text style={{ ...MONO, opacity: r.excluido ? 0.4 : 1 }}>{fmt(v)}</Text>
      } },
    { title: 'INSS', dataIndex: 'inss', width: 88, align: 'right',
      render: (v, r) => {
        const sup = !r.excluido && r.rend_trib_13 > 0
        return sup
          ? <Tooltip title="Zerado na soma — linha com 13º salário"><Text style={{ ...MONO, opacity: 0.35, textDecoration: 'line-through' }}>{fmt(v)}</Text></Tooltip>
          : <Text style={{ ...MONO, opacity: r.excluido ? 0.4 : 1 }}>{fmt(v)}</Text>
      } },
    { title: 'IRRF', dataIndex: 'irrf', width: 88, align: 'right',
      render: (v, r) => {
        const sup = !r.excluido && r.rend_trib_13 > 0
        return sup
          ? <Tooltip title="Zerado na soma — linha com 13º salário"><Text style={{ ...MONO, opacity: 0.35, textDecoration: 'line-through', color: '#cf1322' }}>{fmt(v)}</Text></Tooltip>
          : <Text style={{ ...MONO, color: r.excluido ? undefined : '#cf1322', opacity: r.excluido ? 0.4 : 1 }}>{fmt(v)}</Text>
      } },
    { title: '13º Bruto', dataIndex: 'rend_trib_13', width: 90, align: 'right',
      render: (v, r) => v > 0
        ? <Text style={{ ...MONO, opacity: r.excluido ? 0.4 : 1 }}>{fmt(v)}</Text>
        : <Text type="secondary" style={FS}>—</Text> },
    { title: 'INSS 13º', dataIndex: 'inss_13', width: 88, align: 'right',
      render: (v, r) => v > 0
        ? <Text style={{ ...MONO, opacity: r.excluido ? 0.4 : 1 }}>{fmt(v)}</Text>
        : <Text type="secondary" style={FS}>—</Text> },
    { title: 'Origem', dataIndex: 'origem', width: 72, align: 'center',
      render: (v, r) => (
        <Tag color={r.excluido ? 'default' : (ORIGEM_COLOR[v] || 'default')}
          style={{ fontSize: 10, padding: '0 4px', opacity: r.excluido ? 0.4 : 1 }}>{v}</Tag>
      ) },
    { title: '', key: 'acoes', width: 68, align: 'center',
      render: (_, row) => {
        if (row.manual_id != null) {
          return (
            <Space size={4}>
              <Button size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); abrirFormEditar(row) }} />
              <Popconfirm title="Remover este ajuste?" onConfirm={() => handleRemover(row.manual_id)} okText="Sim" cancelText="Não">
                <Button size="small" danger icon={<DeleteOutlined />} onClick={e => e.stopPropagation()} />
              </Popconfirm>
            </Space>
          )
        }
        if (isEmpMode && row.tabela && row.tabela !== 'MANUAL') {
          return (
            <Tooltip title={row.excluido ? 'Restaurar na soma' : 'Excluir da soma'}>
              <Button
                type="text" size="small"
                loading={toggling === row.row_id}
                icon={row.excluido
                  ? <UndoOutlined style={{ color: '#52c41a', fontSize: 12 }} />
                  : <StopOutlined style={{ color: '#cf1322', fontSize: 12 }} />}
                onClick={e => { e.stopPropagation(); handleToggle(row) }}
                style={{ padding: '0 4px' }}
              />
            </Tooltip>
          )
        }
        return null
      } },
  ]

  const cols = isEmpMode
    ? colsBase
    : [{ title: 'CPF', dataIndex: 'cpf', width: 120, render: v => <Text style={FS}>{fmtCpf(v)}</Text> }, ...colsBase]

  return (
    <Modal
      open={open} onCancel={onClose}
      title={
        isEmpMode
          ? <Space><CalendarOutlined /><span>Lançamentos — {preloadRow.nome} ({fmtCpf(preloadRow.cpf)})</span></Space>
          : 'Ajustes Manuais da Emissão'
      }
      footer={null} width={1150} destroyOnClose
    >
      <div style={{ marginBottom: 8 }}>
        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={abrirFormNovo}>
          Novo Ajuste
        </Button>
      </div>

      <Table
        dataSource={linhas} columns={cols}
        rowKey={(r, i) => `${r.competencia ?? ''}_${r.origem ?? ''}_${i}`}
        size="small" pagination={false} loading={carregando}
        scroll={{ y: 280, x: 760 }}
        rowClassName={r => r.excluido ? 'row-excluida' : ''}
        onRow={(row) => ({
          style: { background: row.manual_id != null ? '#f6ffed' : undefined,
                   cursor:     row.manual_id != null ? 'pointer' : 'default' },
          onClick: () => row.manual_id != null && abrirFormEditar(row),
        })}
        summary={isEmpMode ? () => {
          const ativo = linhas.filter(r => !r.excluido)
          const sup = r => r.rend_trib_13 > 0
          const tr  = ativo.reduce((s, r) => s + (sup(r) ? 0 : r.rend_trib), 0)
          const ins = ativo.reduce((s, r) => s + (sup(r) ? 0 : r.inss), 0)
          const ir  = ativo.reduce((s, r) => s + (sup(r) ? 0 : r.irrf), 0)
          const r13 = ativo.reduce((s, r) => s + r.rend_trib_13, 0)
          const i13 = ativo.reduce((s, r) => s + (r.inss_13 || 0), 0)
          const excl = linhas.filter(r => r.excluido).length
          const offset = isEmpMode ? 0 : 1
          return (
            <Table.Summary.Row style={{ fontWeight: 600, background: '#fafafa' }}>
              <Table.Summary.Cell index={0} colSpan={2 + offset}>
                Total{excl > 0 && <Text type="secondary" style={{ fontSize: 10, marginLeft: 6 }}>({excl} excluído{excl > 1 ? 's' : ''})</Text>}
              </Table.Summary.Cell>
              <Table.Summary.Cell index={2 + offset} align="right"><Text style={MONO}>{fmt(tr)}</Text></Table.Summary.Cell>
              <Table.Summary.Cell index={3 + offset} align="right"><Text style={MONO}>{fmt(ins)}</Text></Table.Summary.Cell>
              <Table.Summary.Cell index={4 + offset} align="right"><Text style={{ ...MONO, color: '#cf1322' }}>{fmt(ir)}</Text></Table.Summary.Cell>
              <Table.Summary.Cell index={5 + offset} align="right"><Text style={MONO}>{fmt(r13)}</Text></Table.Summary.Cell>
              <Table.Summary.Cell index={6 + offset} align="right">{i13 > 0 && <Text style={MONO}>{fmt(i13)}</Text>}</Table.Summary.Cell>
              <Table.Summary.Cell index={7 + offset} colSpan={2} />
            </Table.Summary.Row>
          )
        } : undefined}
      />

      {formVisible && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ border: '1px solid #b7eb8f', borderRadius: 6, padding: '12px 16px', background: '#f6ffed' }}>
            <Text style={{ fontSize: 12, color: '#389e0d', fontWeight: 600 }}>
              {editando ? 'Editando ajuste manual' : 'Novo ajuste manual'}
            </Text>
            <Form form={form} layout="vertical" onFinish={handleSalvar} style={{ marginTop: 10 }}
              initialValues={{ rend_trib: 0, inss: 0, irrf: 0, rend_trib_13: 0, inss_13: 0, irrf_13: 0 }}>
              {isEmpMode && <Form.Item name="cpf" hidden><Input /></Form.Item>}
              <Space wrap align="start" size={8}>
                {!isEmpMode && (
                  <Form.Item name="cpf" label="CPF" style={{ marginBottom: 8 }} rules={[{ required: true, message: 'Informe o CPF' }]}>
                    <Input style={{ width: 130 }} maxLength={14} placeholder="11 dígitos" />
                  </Form.Item>
                )}
                <Form.Item name="empresa" label="Emp." style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: 75 }} min={1} />
                </Form.Item>
                <Form.Item name="competencia" label="Competência" style={{ marginBottom: 8 }}
                  rules={[{ required: true, message: 'Informe YYYY-MM' }, { pattern: /^\d{4}-\d{2}$/, message: 'Formato: YYYY-MM' }]}>
                  <Input style={{ width: 100 }} placeholder="2025-11"
                    onChange={e => {
                      const v = e.target.value
                      if (/^\d{4}-\d{2}$/.test(v)) {
                        const [ano, mes] = v.split('-').map(Number)
                        form.setFieldValue('dt_pagto', `${v}-${String(new Date(ano, mes, 0).getDate()).padStart(2, '0')}`)
                      }
                    }} />
                </Form.Item>
                <Form.Item name="dt_pagto" label="Dt. Pagto" style={{ marginBottom: 8 }}>
                  <Input style={{ width: 110 }} placeholder="2025-11-30" />
                </Form.Item>
                <Form.Item name="cod_receita" label="Cod. Rec." style={{ marginBottom: 8 }}>
                  <Input style={{ width: 85 }} placeholder="056107" />
                </Form.Item>
                <Form.Item name="rend_trib" label="Rend. Trib." style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: 115 }} step={0.01} controls={false} />
                </Form.Item>
                <Form.Item name="inss" label="INSS" style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: 100 }} step={0.01} controls={false} />
                </Form.Item>
                <Form.Item name="irrf" label="IRRF" style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: 100 }} step={0.01} controls={false} />
                </Form.Item>
                <Form.Item name="rend_trib_13" label="13º Bruto" style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: 100 }} step={0.01} controls={false} />
                </Form.Item>
                <Form.Item name="inss_13" label="INSS 13º" style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: 100 }} step={0.01} controls={false} />
                </Form.Item>
                <Form.Item name="irrf_13" label="IRRF 13º" style={{ marginBottom: 8 }}>
                  <InputNumber style={{ width: 100 }} step={0.01} controls={false} />
                </Form.Item>
              </Space>
              <Space align="start">
                <Form.Item name="obs" label="Obs." style={{ marginBottom: 8, width: 380 }}>
                  <Input placeholder="Ex.: INSS férias não veio no S-5002" />
                </Form.Item>
                <Form.Item label=" " style={{ marginBottom: 8 }}>
                  <Space>
                    <Button type="primary" htmlType="submit" loading={salvando} size="small">
                      {editando ? 'Atualizar' : 'Salvar'}
                    </Button>
                    <Button size="small" onClick={() => { setFormVisible(false); setEditando(null) }}>
                      Cancelar
                    </Button>
                  </Space>
                </Form.Item>
              </Space>
            </Form>
          </div>
        </>
      )}
    </Modal>
  )
}

export default function Informes() {
  const [dados, setDados]         = useState([])
  const [filtrado, setFiltrado]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [jobStatus, setJobStatus] = useState(null)
  const [jobMsg, setJobMsg]       = useState('')
  const [pdfModal, setPdfModal]   = useState(null)
  const [ajustesOpen, setAjustesOpen]       = useState(false)
  const [ajustesPreload, setAjustesPreload] = useState(null)
  const [filtroId, setFiltroId]   = useState('identificados')
  const [busca, setBusca]         = useState('')
  const pollRef = useRef(null)

  const carregar = () => {
    setLoading(true)
    getInformes()
      .then(r => { setDados(r.data); aplicarFiltros(r.data, filtroId, busca) })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    carregar()
    return () => clearInterval(pollRef.current)
  }, [])

  const aplicarFiltros = (base, fId, q) => {
    let arr = base
    if (fId === 'identificados') arr = arr.filter(r => r.identificado)
    if (fId === 'nao_id')        arr = arr.filter(r => !r.identificado)
    if (q) {
      const lq = q.toLowerCase()
      arr = arr.filter(r => r.nome.toLowerCase().includes(lq) || r.cpf.includes(lq))
    }
    setFiltrado(arr)
  }

  const handleFiltroId = (f) => { setFiltroId(f); aplicarFiltros(dados, f, busca) }
  const handleBusca    = (q) => { setBusca(q);    aplicarFiltros(dados, filtroId, q) }

  const handleGerar = () => {
    setJobStatus('running')
    setJobMsg('')
    gerarInformes()
      .then(r => {
        const jobId = r.data.job_id
        clearInterval(pollRef.current)
        pollRef.current = setInterval(async () => {
          try {
            const jr = await getJob(jobId)
            if (jr.data.status !== 'running') {
              clearInterval(pollRef.current)
              setJobStatus(jr.data.status)
              setJobMsg(jr.data.mensagem)
              carregar()
            }
          } catch {}
        }, 2000)
      })
      .catch(() => { setJobStatus('erro'); setJobMsg('Erro ao disparar geracao.') })
  }

  const abrirVisualizador = (record) => {
    setPdfModal({ url: pdfUrl(record.cod_empresa, record.cpf), nome: record.nome })
  }

  const handleAjustar = (record) => { setAjustesPreload(record); setAjustesOpen(true) }

  const naoId       = dados.filter(d => !d.identificado).length
  const totalGerados = dados.filter(d => d.pdf_existe && d.identificado).length
  const totalId      = dados.filter(d => d.identificado).length

  const colunas = [
    {
      title: '',
      key: 'acoes',
      width: 105,
      align: 'center',
      filters: [{ text: 'PDF Gerado', value: true }, { text: 'Pendente', value: false }],
      onFilter: (v, r) => r.pdf_existe === v,
      render: (_, record) => (
        <Space size={3}>
          <Tooltip title={
            !record.identificado
              ? 'Não identificado no cadastro'
              : record.tem_ajuste_manual
                ? `Com ajuste manual — ${record.empresa || ''}`
                : `eSocial — ${record.empresa || ''}`
          }>
            <Tag
              color={!record.identificado ? 'error' : record.tem_ajuste_manual ? 'orange' : 'blue'}
              style={{ fontSize: 10, padding: '0 4px', margin: 0, cursor: 'default' }}
            >
              {!record.identificado ? '!' : record.tem_ajuste_manual ? 'M' : 'eS'}
            </Tag>
          </Tooltip>

          {record.identificado ? (
            record.pdf_existe ? (
              <>
                <Tooltip title="Visualizar PDF">
                  <Button type="text" size="small" icon={<EyeOutlined />}
                    style={{ padding: '0 3px', color: '#1677ff' }}
                    onClick={() => abrirVisualizador(record)} />
                </Tooltip>
                <Tooltip title="Baixar PDF">
                  <Button type="text" size="small" icon={<DownloadOutlined />}
                    style={{ padding: '0 3px' }}
                    href={pdfUrl(record.cod_empresa, record.cpf)} target="_blank" />
                </Tooltip>
              </>
            ) : (
              <Tooltip title="PDF ainda não gerado">
                <ClockCircleOutlined style={{ color: '#bfbfbf', fontSize: 13 }} />
              </Tooltip>
            )
          ) : (
            <Tooltip title="PDF não gerado — CPF não identificado no cadastro">
              <StopOutlined style={{ color: '#bfbfbf', fontSize: 13 }} />
            </Tooltip>
          )}

          <Tooltip title="Ajustes manuais">
            <Button type="text" size="small" icon={<EditOutlined />}
              style={{ padding: '0 3px' }}
              onClick={() => handleAjustar(record)} />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Nome',
      dataIndex: 'nome',
      key: 'nome',
      ellipsis: true,
      width: 210,
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
      title: 'Rend. Trib.',
      dataIndex: 'rend_trib',
      key: 'rend_trib',
      width: 120,
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
      title: '13º Bruto',
      dataIndex: 'rend_trib_13',
      key: 'rend_trib_13',
      width: 105,
      align: 'right',
      render: v => v > 0
        ? <Text style={MONO}>R$ {fmt(v)}</Text>
        : <Text type="secondary" style={FS}>—</Text>,
    },
    {
      title: '13º Líquido',
      dataIndex: 'decimo_terceiro_liquido',
      key: 'dec13',
      width: 105,
      align: 'right',
      render: v => v > 0
        ? <Text style={{ ...MONO, color: '#389e0d' }}>R$ {fmt(v)}</Text>
        : <Text type="secondary" style={FS}>—</Text>,
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>Informes de Rendimento 2025</Title>
      <Paragraph type="secondary">
        Visualize os valores consolidados, abra ou baixe os PDFs individuais.
      </Paragraph>

      {naoId > 0 && (
        <Alert
          type="warning" showIcon icon={<WarningOutlined />}
          message={`${naoId} CPF${naoId > 1 ? 's' : ''} não identificado${naoId > 1 ? 's' : ''} no cadastro — PDF não será gerado para estes`}
          style={{ marginBottom: 12 }}
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Space wrap align="center">
          <Button
            type="primary" size="small"
            icon={jobStatus === 'running' ? <SyncOutlined spin /> : <PrinterOutlined />}
            onClick={handleGerar}
            disabled={jobStatus === 'running'}
          >
            {jobStatus === 'running' ? 'Gerando PDFs...' : 'Gerar PDFs (identificados)'}
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => { setAjustesPreload(null); setAjustesOpen(true) }}>
            Ajustes Manuais
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={carregar}>Atualizar</Button>
          <Text type="secondary" style={FS}>{totalGerados} de {totalId} PDFs gerados</Text>
        </Space>

        {jobStatus === 'ok' && (
          <Alert type="success" message="PDFs gerados com sucesso!" style={{ marginTop: 12 }} showIcon />
        )}
        {jobStatus === 'erro' && (
          <Alert type="error" message={`Erro: ${jobMsg}`} style={{ marginTop: 12 }} showIcon />
        )}
      </Card>

      <Card>
        <Space wrap style={{ marginBottom: 10 }}>
          <Button size="small"
            type={filtroId === 'todos' ? 'primary' : 'default'}
            onClick={() => handleFiltroId('todos')}>
            Todos ({dados.length})
          </Button>
          <Button size="small"
            type={filtroId === 'identificados' ? 'primary' : 'default'}
            onClick={() => handleFiltroId('identificados')}>
            Identificados ({totalId})
          </Button>
          <Button size="small"
            type={filtroId === 'nao_id' ? 'primary' : 'default'}
            danger={naoId > 0}
            onClick={() => handleFiltroId('nao_id')}>
            Não identificados ({naoId})
          </Button>
          <Search
            placeholder="Buscar por nome ou CPF"
            onSearch={handleBusca}
            onChange={e => handleBusca(e.target.value)}
            style={{ width: 240 }}
            size="small"
            allowClear
          />
          <Text type="secondary" style={FS}>{filtrado.length} beneficiario(s)</Text>
        </Space>

        <Table
          dataSource={filtrado}
          columns={colunas}
          rowKey="cpf"
          loading={loading}
          size="small"
          style={{ fontSize: 11 }}
          pagination={{ pageSize: 30, showSizeChanger: true }}
          scroll={{ x: 900 }}
          onRow={(record) => ({
            style: { cursor: record.pdf_existe && record.identificado ? 'pointer' : 'default' },
            onDoubleClick: () => record.pdf_existe && record.identificado && abrirVisualizador(record),
          })}
          summary={(pageData) => {
            const totalRend = pageData.reduce((s, r) => s + r.rend_trib, 0)
            const totalInss = pageData.reduce((s, r) => s + r.inss, 0)
            const totalIrrf = pageData.reduce((s, r) => s + r.irrf, 0)
            return (
              <Table.Summary.Row style={{ fontWeight: 600, background: '#fafafa' }}>
                <Table.Summary.Cell index={0} colSpan={3}>Total da página</Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="right">
                  <Text style={MONO}>R$ {fmt(totalRend)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">
                  <Text style={MONO}>R$ {fmt(totalInss)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  <Text style={{ ...MONO, color: '#cf1322' }}>R$ {fmt(totalIrrf)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={6} colSpan={2} />
              </Table.Summary.Row>
            )
          }}
        />
      </Card>

      <Modal
        open={!!pdfModal} onCancel={() => setPdfModal(null)}
        title={<Space><FilePdfOutlined style={{ color: '#cf1322' }} /><span>{pdfModal?.nome}</span></Space>}
        footer={<Button icon={<DownloadOutlined />} href={pdfModal?.url} target="_blank" type="primary">Baixar PDF</Button>}
        width="80vw" style={{ top: 20 }}
        styles={{ body: { padding: 0, height: '80vh' } }}
        destroyOnClose
      >
        {pdfModal && (
          <iframe src={pdfModal.url} title="Informe de Rendimento"
            width="100%" height="100%" style={{ border: 'none', display: 'block' }} />
        )}
      </Modal>

      <AjustesManuaisModal
        open={ajustesOpen}
        onClose={() => { setAjustesOpen(false); setAjustesPreload(null) }}
        onSaved={carregar}
        preloadRow={ajustesPreload}
      />
    </div>
  )
}
