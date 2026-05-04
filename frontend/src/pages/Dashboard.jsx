import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, Table, Tag, Typography, Spin, Alert } from 'antd'
import {
  UserOutlined, FileTextOutlined, FilePdfOutlined,
  DollarOutlined, BankOutlined, SafetyOutlined,
} from '@ant-design/icons'
import { getDashboard } from '../api'

const { Title, Text } = Typography

const fmt = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export default function Dashboard() {
  const [dados, setDados] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    getDashboard()
      .then(r => setDados(r.data))
      .catch(e => setErro(e.response?.data?.detail || 'Não foi possível conectar ao banco de dados.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Spin size="large" style={{ display: 'block', marginTop: 80, textAlign: 'center' }} />
  if (erro)   return <Alert type="error" message={erro} style={{ margin: 24 }} />

  const cols = [
    { title: 'Arquivo', dataIndex: 'arquivo', key: 'arquivo', ellipsis: true },
    { title: 'Competência', dataIndex: 'competencia', key: 'competencia', width: 120 },
    { title: 'CPF', dataIndex: 'cpf', key: 'cpf', width: 140 },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        Dashboard — Ano-Calendário {dados.ano_cal}
      </Title>

      {/* Linha 1 — Beneficiários e PDFs */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Beneficiários"
              value={dados.beneficiarios}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Registros S-1210"
              value={dados.registros_s1210}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Registros Complementar"
              value={dados.registros_compl}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="PDFs Gerados"
              value={dados.pdfs_gerados}
              prefix={<FilePdfOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Linha 2 — Valores financeiros */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Total Rendimentos Tributáveis"
              value={fmt(dados.total_rend)}
              prefix={<DollarOutlined />}
              suffix="R$"
              valueStyle={{ color: '#1677ff', fontSize: 20 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Total INSS Retido"
              value={fmt(dados.total_inss)}
              prefix={<BankOutlined />}
              suffix="R$"
              valueStyle={{ color: '#fa8c16', fontSize: 20 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Total IRRF"
              value={fmt(dados.total_irrf)}
              prefix={<SafetyOutlined />}
              suffix="R$"
              valueStyle={{ color: '#f5222d', fontSize: 20 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Linha 3 — 13º */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="13º Salário Bruto"
              value={fmt(dados.total_rend13)}
              suffix="R$"
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="INSS sobre 13º"
              value={fmt(dados.total_inss13)}
              suffix="R$"
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="IRRF sobre 13º"
              value={fmt(dados.total_irrf13)}
              suffix="R$"
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Últimas importações */}
      <Card
        title="Últimas Importações (S-1210)"
        style={{ marginTop: 24 }}
        size="small"
      >
        <Table
          dataSource={dados.ultimas_importacoes}
          columns={cols}
          rowKey="arquivo"
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  )
}
