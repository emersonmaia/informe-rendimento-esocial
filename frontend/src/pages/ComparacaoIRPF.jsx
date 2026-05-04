import { useEffect, useState } from 'react'
import {
  Card, Col, Row, Select, Typography, Space,
  InputNumber, Table, Tag, Alert, Spin, Divider, Button,
} from 'antd'
import { ReloadOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { getInformes, getIrpfTotais } from '../api'

const { Title, Text, Paragraph } = Typography

const fmt = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const fmtCpf = (cpf) => {
  const c = (cpf || '').replace(/\D/g, '')
  return c.length === 11
    ? `${c.slice(0,3)}.${c.slice(3,6)}.${c.slice(6,9)}-${c.slice(9)}`
    : cpf
}

const LINHAS = [
  { key: 'rend_trib',              label: 'Rendimentos Tributáveis',      cor: '#1677ff' },
  { key: 'inss',                   label: 'INSS Retido',                  cor: '#fa8c16' },
  { key: 'irrf',                   label: 'IRRF',                         cor: '#cf1322' },
  { key: 'rend_trib_13',           label: '13º Salário Bruto',            cor: undefined },
  { key: 'inss_13',                label: 'INSS sobre 13º',               cor: '#fa8c16' },
  { key: 'irrf_13',                label: 'IRRF sobre 13º',               cor: '#cf1322' },
  { key: 'decimo_terceiro_liquido', label: '13º Líquido (declarar)', cor: '#389e0d' },
]

const TOLERANCIA = 0.02

function DiffTag({ diff }) {
  const abs = Math.abs(diff)
  if (abs <= TOLERANCIA) return <Tag icon={<CheckCircleOutlined />} color="success">OK</Tag>
  const sinal = diff > 0 ? '+' : ''
  return (
    <Tag icon={<WarningOutlined />} color="error">
      {sinal}R$ {fmt(diff)}
    </Tag>
  )
}

export default function ComparacaoIRPF() {
  const [beneficiarios, setBeneficiarios] = useState([])
  const [loadingList, setLoadingList]     = useState(true)
  const [cpfSel, setCpfSel]               = useState(null)
  const [sistema, setSistema]             = useState(null)
  const [loadingSist, setLoadingSist]     = useState(false)
  const [irpf, setIrpf]                   = useState({})

  useEffect(() => {
    getInformes()
      .then(r => setBeneficiarios(r.data))
      .finally(() => setLoadingList(false))
  }, [])

  const handleSelecionar = (cpf) => {
    setCpfSel(cpf)
    setSistema(null)
    setIrpf({})
    setLoadingSist(true)
    getIrpfTotais(cpf)
      .then(r => setSistema(r.data))
      .finally(() => setLoadingSist(false))
  }

  const handleIrpfChange = (key, val) => {
    setIrpf(prev => ({ ...prev, [key]: val ?? 0 }))
  }

  const benefSel = beneficiarios.find(b => b.cpf === cpfSel)
  const algumaDivergencia = sistema && LINHAS.some(l => {
    const sis  = sistema[l.key] ?? 0
    const irpfVal = irpf[l.key] ?? 0
    return Math.abs(sis - irpfVal) > TOLERANCIA
  })
  const irpfPreenchido = Object.keys(irpf).length > 0

  const colunas = [
    { title: 'Campo', dataIndex: 'label', key: 'label', width: 220 },
    {
      title: 'Nosso Sistema', dataIndex: 'sistema', key: 'sis', width: 170, align: 'right',
      render: (v, r) => (
        <Text style={{ fontFamily: 'monospace', color: r.cor, fontWeight: 600 }}>
          R$ {fmt(v)}
        </Text>
      ),
    },
    {
      title: 'Declaração IRPF', key: 'irpf', width: 200, align: 'right',
      render: (_, r) => (
        <InputNumber
          prefix="R$"
          value={irpf[r.key] ?? null}
          onChange={(v) => handleIrpfChange(r.key, v)}
          style={{ width: 170 }}
          decimalSeparator=","
          precision={2}
          min={0}
          placeholder="0,00"
        />
      ),
    },
    {
      title: 'Diferença', key: 'diff', width: 150, align: 'center',
      render: (_, r) => {
        if (!irpfPreenchido) return <Text type="secondary">—</Text>
        const sis  = r.sistema
        const irpfVal = irpf[r.key] ?? 0
        return <DiffTag diff={sis - irpfVal} />
      },
    },
  ]

  const tableData = sistema
    ? LINHAS.map(l => ({
        key:     l.key,
        label:   l.label,
        cor:     l.cor,
        sistema: sistema[l.key] ?? 0,
      }))
    : []

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>Comparação com Declaração IRPF</Title>
      <Paragraph type="secondary">
        Selecione um beneficiário, informe os valores da declaração de IRPF e compare
        com o que o sistema registrou. Diferenças acima de R$ 0,02 são sinalizadas.
      </Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap align="center">
          <Text strong>Beneficiário:</Text>
          {loadingList
            ? <Spin size="small" />
            : (
              <Select
                showSearch
                placeholder="Selecione um funcionário"
                style={{ minWidth: 320 }}
                onChange={handleSelecionar}
                value={cpfSel}
                filterOption={(input, opt) =>
                  opt.label?.toLowerCase().includes(input.toLowerCase())
                }
                options={beneficiarios.map(b => ({
                  value: b.cpf,
                  label: `${b.nome} — ${fmtCpf(b.cpf)}`,
                }))}
              />
            )
          }
          {benefSel && (
            <Text type="secondary">
              {benefSel.empresa} · CPF {fmtCpf(cpfSel)}
            </Text>
          )}
        </Space>
      </Card>

      {cpfSel && (
        <>
          {loadingSist
            ? <Spin style={{ display: 'block', marginTop: 40, textAlign: 'center' }} />
            : sistema && (
              <>
                {irpfPreenchido && (
                  <Alert
                    type={algumaDivergencia ? 'warning' : 'success'}
                    showIcon
                    icon={algumaDivergencia ? <WarningOutlined /> : <CheckCircleOutlined />}
                    message={algumaDivergencia
                      ? 'Há divergências entre o sistema e a declaração IRPF'
                      : 'Todos os valores conferem com a declaração IRPF'
                    }
                    style={{ marginBottom: 16 }}
                  />
                )}

                <Card
                  title={`Comparativo — ${benefSel?.nome || cpfSel}`}
                  extra={
                    <Button
                      size="small" icon={<ReloadOutlined />}
                      onClick={() => handleSelecionar(cpfSel)}
                    >
                      Recarregar sistema
                    </Button>
                  }
                >
                  <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                    Preencha a coluna "Declaração IRPF" com os valores informados pelo funcionário
                    em sua declaração de ajuste anual. A diferença é calculada como
                    <Text code> Sistema − IRPF</Text>.
                  </Paragraph>

                  <Table
                    dataSource={tableData}
                    columns={colunas}
                    rowKey="key"
                    size="small"
                    pagination={false}
                    scroll={{ x: 700 }}
                  />

                  <Divider />

                  <Row gutter={24}>
                    <Col>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Rendimento líquido do 13º = 13º Bruto − INSS 13º − IRRF 13º.
                        Este é o valor que o funcionário deve informar na ficha de "Rendimentos Isentos e Não Tributáveis".
                      </Text>
                    </Col>
                  </Row>
                </Card>
              </>
            )
          }
        </>
      )}

      {!cpfSel && (
        <Alert
          type="info"
          message="Selecione um beneficiário para iniciar a comparação"
          showIcon
        />
      )}
    </div>
  )
}
