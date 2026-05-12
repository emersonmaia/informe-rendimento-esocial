import { useEffect, useState } from 'react'
import {
  Button, Card, Table, Tag, Typography, Space,
  Alert, Row, Col, Statistic, DatePicker, Tooltip, message,
} from 'antd'
import {
  WarningOutlined, CloseCircleOutlined, ReloadOutlined, DownloadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { getPendenciasEsocial, getDashboard } from '../api'

const { Title, Text } = Typography

const MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

const fmtCpf = (cpf) => {
  const c = (cpf || '').replace(/\D/g, '')
  return c.length === 11
    ? `${c.slice(0,3)}.${c.slice(3,6)}.${c.slice(6,9)}-${c.slice(9)}`
    : cpf
}

const fmt = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const pendenciaTag = (p) => {
  if (p === 'SEM_ESOCIAL')
    return <Tag icon={<CloseCircleOutlined />} color="error">Sem S-1210</Tag>
  if (p === 'INSS_ZERO')
    return <Tag icon={<WarningOutlined />} color="orange">INSS = 0</Tag>
  return null
}

function exportCsv(dados) {
  const header = 'Mês;Nome;CPF;Comp. Pagto;Dt Pgto;Folha INSS;eSocial INSS;Pendência'
  const rows = dados.map(r => [
    `${String(r.mes_comp).padStart(2,'0')}/${r.ano_comp}`,
    r.nome,
    fmtCpf(r.cpf),
    r.competencia_pagto,
    r.data_pgto,
    String(r.folha_inss).replace('.',','),
    String(r.es_inss).replace('.',','),
    r.pendencia,
  ].join(';'))
  const blob = new Blob(['﻿' + [header, ...rows].join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `pendencias_esocial_${dayjs().format('YYYYMMDD')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function PendenciasEsocial() {
  const [ano, setAno]         = useState(null)
  const [dados, setDados]     = useState([])
  const [loading, setLoading] = useState(false)
  const [erro, setErro]       = useState(null)

  const carregar = (a) => {
    if (!a) return
    setLoading(true)
    setErro(null)
    getPendenciasEsocial(a)
      .then(r => setDados(r.data))
      .catch(e => setErro(e.response?.data?.detail || 'Erro ao carregar'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getDashboard()
      .then(r => {
        const a = r.data.ano_cal || dayjs().year() - 1
        setAno(a)
        carregar(a)
      })
      .catch(() => {
        const a = dayjs().year() - 1
        setAno(a)
        carregar(a)
      })
  }, [])

  const nSemEsocial = dados.filter(r => r.pendencia === 'SEM_ESOCIAL').length
  const nInssZero   = dados.filter(r => r.pendencia === 'INSS_ZERO').length

  const mesesComPendencia = [...new Set(dados.map(r => r.mes_comp))].sort((a,b) => a-b)

  const colunas = [
    {
      title: 'Mês', key: 'mes', width: 80, align: 'center',
      render: (_, r) => `${String(r.mes_comp).padStart(2,'0')}/${r.ano_comp}`,
      filters: mesesComPendencia.map(m => ({
        text: `${String(m).padStart(2,'0')} - ${MESES[m-1]}`,
        value: m,
      })),
      onFilter: (v, r) => r.mes_comp === v,
    },
    {
      title: 'Pendência', dataIndex: 'pendencia', key: 'pend', width: 130, align: 'center',
      render: pendenciaTag,
      filters: [
        { text: 'Sem S-1210', value: 'SEM_ESOCIAL' },
        { text: 'INSS = 0',   value: 'INSS_ZERO' },
      ],
      onFilter: (v, r) => r.pendencia === v,
    },
    {
      title: 'Nome', dataIndex: 'nome', key: 'nome', ellipsis: true,
      sorter: (a, b) => a.nome.localeCompare(b.nome),
    },
    {
      title: 'CPF', dataIndex: 'cpf', key: 'cpf', width: 145,
      render: v => (
        <Space size={4}>
          <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{fmtCpf(v)}</Text>
          <Button
            size="small" type="link" style={{ padding: 0, fontSize: 11 }}
            onClick={() => { navigator.clipboard.writeText(v); message.success('CPF copiado!', 1) }}
          >
            copiar
          </Button>
        </Space>
      ),
    },
    {
      title: 'Comp. Pagto', dataIndex: 'competencia_pagto', key: 'cpagto',
      width: 110, align: 'center',
    },
    {
      title: 'Dt Pgto', dataIndex: 'data_pgto', key: 'pgto', width: 105, align: 'center',
      render: v => v || <Text type="secondary">—</Text>,
    },
    {
      title: <Tooltip title="INSS na folha de pagamento">Folha INSS</Tooltip>,
      dataIndex: 'folha_inss', key: 'fi', width: 110, align: 'right',
      render: v => <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>,
    },
    {
      title: <Tooltip title="INSS no eSocial (S-1210/COMPL) para a competência de pagamento">eSocial INSS</Tooltip>,
      dataIndex: 'es_inss', key: 'ei', width: 110, align: 'right',
      render: v => v > 0
        ? <Text style={{ fontFamily: 'monospace' }}>R$ {fmt(v)}</Text>
        : <Text type="danger" style={{ fontFamily: 'monospace' }}>R$ 0,00</Text>,
    },
    {
      title: <Tooltip title="Número de eventos S-1210 encontrados para este CPF/competência">Ev.</Tooltip>,
      dataIndex: 'qtd_eventos', key: 'ev', width: 55, align: 'center',
      render: v => v === 0 ? <Text type="secondary">—</Text> : v,
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 4 }}>
        Pendências de Pagamento eSocial — Ano {ano}
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        Funcionários na folha cujo S-1210 <b>não foi informado</b> no eSocial ou tem <b>INSS = 0</b>.
        Use a lista para localizar e informar os pagamentos no portal.
      </Text>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={8}>
          <Card size="small" style={{ borderColor: '#ffa39e' }}>
            <Statistic
              title="Total de pendências" value={dados.length}
              valueStyle={{ color: '#cf1322', fontSize: 22 }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col xs={8}>
          <Card size="small" style={{ borderColor: '#ffa39e' }}>
            <Statistic
              title="Sem S-1210 no eSocial" value={nSemEsocial}
              valueStyle={{ color: '#cf1322', fontSize: 22 }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={8}>
          <Card size="small" style={{ borderColor: '#fa8c16' }}>
            <Statistic
              title="S-1210 com INSS = 0" value={nInssZero}
              valueStyle={{ color: '#fa8c16', fontSize: 22 }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {dados.length > 0 && (
        <Alert
          type="warning" showIcon
          message={`${dados.length} pendência${dados.length > 1 ? 's' : ''} encontrada${dados.length > 1 ? 's' : ''}`}
          description={
            <span>
              Acesse o portal eSocial → <b>Folha de Pagamento com guia DARF</b> → selecione o período
              e informe o pagamento para cada CPF listado. Use o botão <b>copiar</b> ao lado do CPF.
            </span>
          }
          style={{ marginBottom: 12 }}
        />
      )}

      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <DatePicker
            picker="year"
            value={ano ? dayjs(`${ano}-01-01`) : null}
            onChange={v => { if (v) { setAno(v.year()); carregar(v.year()) } }}
            allowClear={false}
            format="YYYY"
          />
          <Button icon={<ReloadOutlined />} onClick={() => carregar(ano)} loading={loading}>
            Atualizar
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => exportCsv(dados)}
            disabled={dados.length === 0}
          >
            Exportar CSV
          </Button>
        </Space>
      </Card>

      {erro && <Alert type="error" message={erro} style={{ marginBottom: 12 }} showIcon />}

      <Card>
        <Table
          dataSource={dados}
          columns={colunas}
          rowKey={(r) => `${r.mes_comp}-${r.cpf}`}
          loading={loading}
          size="small"
          pagination={{ pageSize: 50, showSizeChanger: true, showTotal: t => `${t} pendências` }}
          scroll={{ x: 1000 }}
          rowClassName={(r) => r.pendencia === 'SEM_ESOCIAL' ? 'row-sem-esocial' : 'row-inss-zero'}
          locale={{ emptyText: dados.length === 0 && !loading ? '✓ Nenhuma pendência encontrada!' : 'Carregando...' }}
        />
      </Card>

      <style>{`
        .row-sem-esocial td { background: #fff1f0 !important; }
        .row-inss-zero   td { background: #fff7e6 !important; }
      `}</style>
    </div>
  )
}
