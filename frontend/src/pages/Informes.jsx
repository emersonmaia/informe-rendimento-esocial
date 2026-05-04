import { useState, useEffect, useRef } from 'react'
import {
  Button, Card, Table, Tag, Typography, Space,
  Input, Alert, Modal,
} from 'antd'
import {
  FilePdfOutlined, PrinterOutlined, SyncOutlined,
  ReloadOutlined, EyeOutlined, DownloadOutlined,
} from '@ant-design/icons'
import { getInformes, gerarInformes, getJob, pdfUrl } from '../api'

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

export default function Informes() {
  const [dados, setDados]         = useState([])
  const [filtrado, setFiltrado]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [jobStatus, setJobStatus] = useState(null)
  const [jobMsg, setJobMsg]       = useState('')
  const [pdfModal, setPdfModal]   = useState(null) // { url, nome }
  const pollRef = useRef(null)

  const carregar = () => {
    setLoading(true)
    getInformes()
      .then(r => { setDados(r.data); setFiltrado(r.data) })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    carregar()
    return () => clearInterval(pollRef.current)
  }, [])

  const handleBusca = (valor) => {
    const q = valor.toLowerCase()
    setFiltrado(
      q ? dados.filter(r => r.nome.toLowerCase().includes(q) || r.cpf.includes(q)) : dados
    )
  }

  const handleGerar = () => {
    setJobStatus('running')
    setJobMsg('')
    gerarInformes().then(r => {
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
    }).catch(() => { setJobStatus('erro'); setJobMsg('Erro ao disparar geração.') })
  }

  const abrirVisualizador = (record) => {
    setPdfModal({ url: pdfUrl(record.cod_empresa, record.cpf), nome: record.nome })
  }

  const colunas = [
    {
      title: 'Nome', dataIndex: 'nome', key: 'nome',
      sorter: (a, b) => a.nome.localeCompare(b.nome),
      ellipsis: true, width: 220,
    },
    {
      title: 'CPF', dataIndex: 'cpf', key: 'cpf', width: 140,
      render: cpf => fmtCpf(cpf),
    },
    {
      title: 'Rendimentos', dataIndex: 'rend_trib', key: 'rend_trib', width: 130, align: 'right',
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
      title: '13º Bruto', dataIndex: 'rend_trib_13', key: 'rend_trib_13', width: 110, align: 'right',
      render: v => v > 0
        ? <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>
        : <Text type="secondary">—</Text>,
    },
    {
      title: '13º Líquido', dataIndex: 'decimo_terceiro_liquido', key: 'dec13', width: 110, align: 'right',
      render: v => v > 0
        ? <Text style={{ fontFamily: 'monospace', color: '#389e0d' }}>R$ {fmt(v)}</Text>
        : <Text type="secondary">—</Text>,
    },
    {
      title: 'Ações', dataIndex: 'pdf_existe', key: 'pdf', width: 140, align: 'center',
      filters: [{ text: 'PDF Gerado', value: true }, { text: 'Pendente', value: false }],
      onFilter: (v, r) => r.pdf_existe === v,
      render: (existe, record) =>
        existe ? (
          <Space size={4}>
            <Button
              type="primary" ghost size="small"
              icon={<EyeOutlined />}
              onClick={() => abrirVisualizador(record)}
            />
            <Button
              size="small" icon={<DownloadOutlined />}
              href={pdfUrl(record.cod_empresa, record.cpf)}
              target="_blank"
            />
          </Space>
        ) : (
          <Tag color="warning">Pendente</Tag>
        ),
    },
  ]

  const totalGerados = dados.filter(d => d.pdf_existe).length

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>Informes de Rendimento 2025</Title>
      <Paragraph type="secondary">
        Visualize os valores consolidados, abra ou baixe os PDFs individuais.
      </Paragraph>

      {/* Ações */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap align="center">
          <Button
            type="primary"
            icon={jobStatus === 'running' ? <SyncOutlined spin /> : <PrinterOutlined />}
            onClick={handleGerar}
            disabled={jobStatus === 'running'}
          >
            {jobStatus === 'running' ? 'Gerando PDFs...' : 'Gerar Todos os PDFs'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={carregar}>Atualizar Lista</Button>
          <Text type="secondary">{totalGerados} de {dados.length} PDFs gerados</Text>
        </Space>

        {jobStatus === 'ok' && (
          <Alert type="success" message="PDFs gerados com sucesso!" style={{ marginTop: 12 }} showIcon />
        )}
        {jobStatus === 'erro' && (
          <Alert type="error" message={`Erro: ${jobMsg}`} style={{ marginTop: 12 }} showIcon />
        )}
      </Card>

      {/* Grid */}
      <Card>
        <Space style={{ marginBottom: 12 }}>
          <Search
            placeholder="Buscar por nome ou CPF"
            onSearch={handleBusca}
            onChange={e => handleBusca(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />
          <Text type="secondary">{filtrado.length} beneficiário(s)</Text>
        </Space>

        <Table
          dataSource={filtrado}
          columns={colunas}
          rowKey="cpf"
          loading={loading}
          size="small"
          style={{ fontSize: 12 }}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: 950 }}
          onRow={(record) => ({
            style: { cursor: record.pdf_existe ? 'pointer' : 'default' },
            onDoubleClick: () => record.pdf_existe && abrirVisualizador(record),
          })}
          summary={(pageData) => {
            const totalRend = pageData.reduce((s, r) => s + r.rend_trib, 0)
            const totalInss = pageData.reduce((s, r) => s + r.inss, 0)
            const totalIrrf = pageData.reduce((s, r) => s + r.irrf, 0)
            return (
              <Table.Summary.Row style={{ background: '#fafafa', fontWeight: 600 }}>
                <Table.Summary.Cell index={0} colSpan={2}>Total da página</Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="right">
                  <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(totalRend)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">
                  <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(totalInss)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  <Text style={{ fontFamily: 'monospace', color: '#cf1322' }}>R$ {fmt(totalIrrf)}</Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={6} colSpan={3} />
              </Table.Summary.Row>
            )
          }}
        />
      </Card>

      {/* Modal visualizador de PDF */}
      <Modal
        open={!!pdfModal}
        onCancel={() => setPdfModal(null)}
        title={
          <Space>
            <FilePdfOutlined style={{ color: '#cf1322' }} />
            <span>{pdfModal?.nome}</span>
          </Space>
        }
        footer={
          <Button
            icon={<DownloadOutlined />}
            href={pdfModal?.url}
            target="_blank"
            type="primary"
          >
            Baixar PDF
          </Button>
        }
        width="80vw"
        style={{ top: 20 }}
        styles={{ body: { padding: 0, height: '80vh' } }}
        destroyOnClose
      >
        {pdfModal && (
          <iframe
            src={pdfModal.url}
            title="Informe de Rendimento"
            width="100%"
            height="100%"
            style={{ border: 'none', display: 'block' }}
          />
        )}
      </Modal>
    </div>
  )
}
