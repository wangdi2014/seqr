import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Popup, Icon } from 'semantic-ui-react'
import { Link } from 'react-router-dom'
import styled from 'styled-components'

import { updateFamily } from 'redux/rootReducer'
import { getProjectsByGuid } from 'redux/selectors'
import VariantTagTypeBar from '../graph/VariantTagTypeBar'
import ShowMatchmakerModal from '../buttons/ShowMatchmakerModal'
import PedigreeImagePanel from './view-pedigree-image/PedigreeImagePanel'
import TextFieldView from './view-fields/TextFieldView'
import Sample from './sample'
import { ColoredIcon, InlineHeader } from '../StyledComponents'
import { VerticalSpacer, HorizontalSpacer } from '../Spacers'
import {
  FAMILY_ANALYSIS_STATUS_OPTIONS,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_FIELD_FIRST_SAMPLE,
  FAMILY_FIELD_RENDER_LOOKUP,
  FAMILY_FIELD_OMIM_NUMBER,
} from '../../utils/constants'

const FamilyGrid = styled(({ annotation, offset, ...props }) => <Grid {...props} />)`
  margin-left: ${props => ((props.annotation || props.offset) ? '25px !important' : 'inherit')};
  margin-top: ${props => (props.annotation ? '-33px !important' : 'inherit')};
`

const NoWrap = styled.div`
  white-space: nowrap;
`

const familyFieldRenderProps = {
  [FAMILY_FIELD_ANALYSIS_STATUS]: {
    tagOptions: FAMILY_ANALYSIS_STATUS_OPTIONS,
    tagAnnotation: (value, compact) => (compact ?
      <Popup trigger={<ColoredIcon name="stop" color={value.color} />} content={value.text} position="top center" /> :
      <ColoredIcon name="stop" color={value.color} />
    ),
  },
  [FAMILY_FIELD_ANALYSED_BY]: {
    addConfirm: 'Are you sure you want to add that you analysed this family?',
    fieldDisplay: (analysedByList, compact) => <AnalysedBy analysedByList={analysedByList} compact={compact} />,
  },
  [FAMILY_FIELD_FIRST_SAMPLE]: {
    showEmptyValues: true,
    fieldDisplay: (loadedSample, compact) =>
      <Sample loadedSample={loadedSample} hoverDetails={compact ? 'first loaded' : null} />,
  },
  [FAMILY_FIELD_OMIM_NUMBER]: {
    fieldDisplay: value => <a target="_blank" href={`https://www.omim.org/entry/${value}`}>{value}</a>,
    formFields: [{ name: FAMILY_FIELD_OMIM_NUMBER }],
  },
}


const formatAnalysedByList = analysedByList =>
  analysedByList.map(analysedBy =>
    `${analysedBy.createdBy.displayName || analysedBy.createdBy.email} (${new Date(analysedBy.lastModifiedDate).toLocaleDateString()})`,
  ).join(', ')

export const AnalysedBy = ({ analysedByList, compact }) => {
  if (compact) {
    return [...analysedByList.reduce(
      (acc, analysedBy) => acc.add(analysedBy.createdBy.displayName || analysedBy.createdBy.email), new Set(),
    )].map(
      analysedByUser => <NoWrap key={analysedByUser}>{analysedByUser}</NoWrap>,
    )
  }
  const staffUsers = analysedByList.filter(analysedBy => analysedBy.createdBy.isStaff)
  const externalUsers = analysedByList.filter(analysedBy => !analysedBy.createdBy.isStaff)
  return [
    staffUsers.length > 0 ? <div key="staff"><b>CMG Analysts:</b> {formatAnalysedByList(staffUsers)}</div> : null,
    externalUsers.length > 0 ? <div key="ext"><b>External Collaborators:</b> {formatAnalysedByList(externalUsers)}</div> : null,
  ]
}

AnalysedBy.propTypes = {
  analysedByList: PropTypes.array,
  compact: PropTypes.bool,
}

export const FamilyLayout = ({ leftContent, rightContent, annotation, offset, fields, fieldDisplay, useFullWidth, compact }) =>
  <div>
    {annotation}
    <FamilyGrid annotation={annotation} offset={offset}>
      <Grid.Row>
        <Grid.Column width={3}>
          {leftContent}
        </Grid.Column>
        {compact ? fields.map(field =>
          <Grid.Column width={field.colWidth || 1} key={field.id}>{fieldDisplay(field)}</Grid.Column>,
        ) : <Grid.Column width={(useFullWidth && !rightContent) ? 13 : 10}>{fields.map(field => fieldDisplay(field))}</Grid.Column>
        }
        {rightContent && <Grid.Column width={3}>{rightContent}</Grid.Column>}
      </Grid.Row>
    </FamilyGrid>
  </div>

FamilyLayout.propTypes = {
  fieldDisplay: PropTypes.func,
  fields: PropTypes.array,
  useFullWidth: PropTypes.bool,
  compact: PropTypes.bool,
  offset: PropTypes.bool,
  annotation: PropTypes.node,
  leftContent: PropTypes.node,
  rightContent: PropTypes.node,
}

const SearchLink = ({ project, family, children }) => (
  project.hasNewSearch ? <Link to={`/variant_search/family/${family.familyGuid}`}>{children}</Link>
    : <a href={`/project/${project.deprecatedProjectId}/family/${family.familyId}/mendelian-variant-search`}>{children}</a>
)

SearchLink.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  children: PropTypes.node,
}

const Family = (
  { project, family, fields = [], showVariantDetails, compact, useFullWidth, disablePedigreeZoom,
    showFamilyPageLink, annotation, updateFamily: dispatchUpdateFamily,
  }) => {
  if (!family) {
    return <div>Family Not Found</div>
  }

  const familyField = (field) => {
    const renderDetails = FAMILY_FIELD_RENDER_LOOKUP[field.id]
    const submitFunc = renderDetails.submitArgs ?
      values => dispatchUpdateFamily({ ...values, ...renderDetails.submitArgs }) : dispatchUpdateFamily
    return React.createElement(renderDetails.component || TextFieldView, {
      key: field.id,
      isEditable: project.canEdit && field.canEdit,
      isPrivate: renderDetails.internal,
      fieldName: compact ? null : renderDetails.name,
      field: field.id,
      idField: 'familyGuid',
      initialValues: family,
      onSubmit: submitFunc,
      modalTitle: `${renderDetails.name} for Family ${family.displayName}`,
      compact,
      ...(familyFieldRenderProps[field.id] || {}),
    })
  }

  const leftContent = [
    <InlineHeader
      key="name"
      overrideInline={!compact}
      size="small"
      content={showFamilyPageLink ?
        <Link to={`/project/${project.projectGuid}/family_page/${family.familyGuid}`}>{family.displayName}</Link> :
        family.displayName
      }
    />,
    <PedigreeImagePanel key="pedigree" family={family} disablePedigreeZoom={disablePedigreeZoom} compact={compact} />,
  ]

  const discoveryGenes = project.discoveryTags.filter(tag => tag.familyGuids.includes(family.familyGuid)).reduce(
    (acc, tag) => (tag.mainTranscript.geneSymbol ? [...acc, tag.mainTranscript.geneSymbol] : acc), [],
  )

  const rightContent = showVariantDetails ? [
    <div key="variants">
      <VariantTagTypeBar height={15} width="calc(100% - 2.5em)" project={project} familyGuid={family.familyGuid} sectionLinks={false} />
      <HorizontalSpacer width={10} />
      <SearchLink project={project} family={family}><Icon name="search" /></SearchLink>
      {discoveryGenes.length > 0 &&
        <span>
          <b>Discovery Genes:</b> {[...new Set(discoveryGenes)].join(', ')}
        </span>
      }
    </div>,
    !compact ?
      <div key="links">
        <VerticalSpacer height={20} />
        <SearchLink project={project} family={family}><Icon name="search" /> Variant Search</SearchLink>
        <VerticalSpacer height={10} />
        {project.isMmeEnabled && <ShowMatchmakerModal family={family} />}
      </div> : null,
  ] : null

  return <FamilyLayout
    useFullWidth={useFullWidth}
    compact={compact}
    annotation={annotation}
    fields={fields}
    fieldDisplay={familyField}
    leftContent={leftContent}
    rightContent={rightContent}
  />
}

export { Family as FamilyComponent }

Family.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  fields: PropTypes.array,
  showVariantDetails: PropTypes.bool,
  useFullWidth: PropTypes.bool,
  disablePedigreeZoom: PropTypes.bool,
  compact: PropTypes.bool,
  showFamilyPageLink: PropTypes.bool,
  updateFamily: PropTypes.func,
  annotation: PropTypes.node,
}


const mapStateToProps = (state, ownProps) => ({
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
})

const mapDispatchToProps = {
  updateFamily,
}

export default connect(mapStateToProps, mapDispatchToProps)(Family)
