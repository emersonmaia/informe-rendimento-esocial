import { useState, useEffect, useRef } from 'react'
import {
  Button, Card, Col, Row, Table, Tag, Typography,
  Alert, Space, Divider, Badge, Spin, Popconfirm, message,
} from 'antd'
import {
  SearchOutlined, CloudDownloadOutlined,
  CheckCircleOutlined, SyncOutlined, CloseCircleOutlined, DeleteOutlined,
} from '@ant-design/icons'
import { verificarXmls, importarS1210, importarS1200, importarS2299, getJobImport, listarJobs, limparDados } from '../api'

const { Title, Text, Paragraph } = Typography

const StatusTag = ({ status }) => {
  if (status === 'running') return <Tag icon={<SyncOutlined spin />} color="processing">Executando</Tag>
  if (status === 'ok')      return <Tag icon={<CheckCircleOutlined />} color="success">Concluído</Tag>
  if (status === 'erro')    return <Tag icon={<CloseCircleOutlined />} color="error">Erro</Tag>
  return <Tag>{status}</Tag>
}

export default function Importacao() {
  const [verificando, setVerificando]   = useState(false)
  const [novos, setNovos]               = useState(null)
  const [jobs, setJobs]                 = useState([])
  const [loadingJobs, setLoadingJobs]   = useState(false)
  const [activeJobId, setActiveJobId]   = useState(null)
  const pollRef = useRef(null)

  const carregarJobs = () => {
    setLoadingJobs(true)
    listarJobs()
      .then(r => setJobs(r.data))
      .finally(() => setLoadingJobs(false))
  }

  useEffect(() => {
    carregarJobs()
    return () => clearInterval(pollRef.current)
  }, [])

  const iniciarPolling = (jobId) => {
    setActiveJobId(jobId)
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const r = await getJobImport(jobId)
        setJobs(prev => {
          const outros = prev.filter(j => j.id !== r.data.id)
          return [r.data, ...outros]
        })
        if (r.data.status !== 'running') {
          clearInterval(pollRef.current)
          setActiveJobId(null)
          setNovos(null) // força nova verificação após importar
        }
      } catch {}
    }, 1500)
  }

  const handleVerificar = () => {
    setVerificando(true)
    verificarXmls()
      .then(r => setNovos(r.data))
      .finally(() => setVerificando(false))
  }

  const handleImportarS1210 = () => {
    importarS1210().then(r => iniciarPolling(r.data.job_id))
  }

  const handleImportarS1200 = () => {
    importarS1200().then(r => iniciarPolling(r.data.job_id))
  }

  const handleImportarS2299 = () => {
    importarS2299().then(r => iniciarPolling(r.data.job_id))
  }

  const handleLimpar = () => {
    limparDados()
      .then(r => {
        message.success(`Dados apagados: ${r.data.removidos_s1210} S-1210, ${r.data.removidos_compl} complementares`)
        setNovos(null)
        carregarJobs()
      })
      .catch(e => message.error(e.response?.data?.detail || 'Erro ao limpar dados'))
  }

  const colsNovos = [
    { title: 'Arquivo', dataIndex: 'arquivo', key: 'arquivo', ellipsis: true },
    { title: 'Empresa', dataIndex: 'empresa', key: 'empresa', width: 120 },
  ]

  const colsJobs = [
    { title: 'Tipo', dataIndex: 'tipo', key: 'tipo', width: 100,
      render: t => <Tag color="blue">{t.toUpperCase()}</Tag> },
    { title: 'Status', dataIndex: 'status', key: 'status', width: 140,
      render: s => <StatusTag status={s} /> },
    { title: 'Iniciado', dataIndex: 'iniciado_em', key: 'iniciado_em', width: 180,
      render: v => new Date(v).toLocaleString('pt-BR') },
    { title: 'Resultado', dataIndex: 'mensagem', key: 'mensagem', ellipsis: true,
      render: (msg) => <Text type="secondary" style={{ fontSize: 12 }}>{msg?.split('\n').slice(-3).join(' | ')}</Text> },
  ]

  const isRunning = activeJobId !== null

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>Importação de XMLs eSocial</Title>
      <Paragraph type="secondary">
        Verifique se há arquivos novos nas pastas monitoradas e dispare a importação.
        Os scripts existentes são chamados sem modificação.
      </Paragraph>

      {/* Verificação */}
      <Card title="1. Verificar Arquivos Novos" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button
            icon={<SearchOutlined />}
            onClick={handleVerificar}
            loading={verificando}
            type="default"
          >
            Verificar Pastas Agora
          </Button>

          {novos && (
            <Row gutter={16} style={{ marginTop: 12 }}>
              <Col span={12}>
                <Card
                  size="small"
                  title={
                    <Space>
                      <span>S-1210 (Portal eSocial)</span>
                      <Badge count={novos.total_novos_s1210} showZero color={novos.total_novos_s1210 > 0 ? 'blue' : 'green'} />
                    </Space>
                  }
                >
                  {novos.total_novos_s1210 === 0
                    ? <Alert type="success" message="Nenhum arquivo novo" showIcon />
                    : <Table dataSource={novos.novos_s1210} columns={colsNovos} rowKey="arquivo"
                        size="small" pagination={{ pageSize: 5 }} />
                  }
                </Card>
              </Col>
              <Col span={12}>
                <Card
                  size="small"
                  title={
                    <Space>
                      <span>S-1200 (Retornos)</span>
                      <Badge count={novos.total_novos_s1200} showZero color={novos.total_novos_s1200 > 0 ? 'blue' : 'green'} />
                    </Space>
                  }
                >
                  {novos.total_novos_s1200 === 0
                    ? <Alert type="success" message="Nenhum arquivo novo" showIcon />
                    : <Table dataSource={novos.novos_s1200} columns={[{ title: 'Arquivo', dataIndex: 'arquivo', key: 'arquivo', ellipsis: true }]}
                        rowKey="arquivo" size="small" pagination={{ pageSize: 5 }} />
                  }
                </Card>
              </Col>
            </Row>
          )}
        </Space>
      </Card>

      {/* Importação */}
      <Card title="2. Importar" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button
            type="primary"
            icon={<CloudDownloadOutlined />}
            onClick={handleImportarS1210}
            disabled={isRunning}
          >
            Importar S-1210
          </Button>
          <Button
            icon={<CloudDownloadOutlined />}
            onClick={handleImportarS1200}
            disabled={isRunning}
          >
            Importar S-1200 Complementar
          </Button>
          <Button
            icon={<CloudDownloadOutlined />}
            onClick={handleImportarS2299}
            disabled={isRunning}
          >
            Importar Rescisões S-2299
          </Button>
          {isRunning && <Spin tip="Importando..." />}
        </Space>
        <Divider />
        <Space align="center">
          <Popconfirm
            title="Limpar todos os dados importados?"
            description="Apaga ESOCIAL_S1210 e ESOCIAL_S1210_COMPL do banco ativo. Use para reimportar do zero."
            okText="Sim, apagar"
            cancelText="Cancelar"
            okButtonProps={{ danger: true }}
            onConfirm={handleLimpar}
            disabled={isRunning}
          >
            <Button danger icon={<DeleteOutlined />} disabled={isRunning}>
              Limpar dados importados
            </Button>
          </Popconfirm>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Use antes de reimportar caso o banco esteja com dados incorretos.
          </Text>
        </Space>
      </Card>

      {/* Histórico de jobs */}
      <Card
        title="Histórico de Execuções"
        extra={<Button size="small" onClick={carregarJobs} loading={loadingJobs}>Atualizar</Button>}
      >
        <Table
          dataSource={jobs}
          columns={colsJobs}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          expandable={{
            expandedRowRender: (record) => (
              <pre style={{ fontSize: 11, maxHeight: 200, overflow: 'auto', background: '#f5f5f5', padding: 8 }}>
                {record.mensagem}
              </pre>
            ),
          }}
        />
      </Card>
    </div>
  )
}
