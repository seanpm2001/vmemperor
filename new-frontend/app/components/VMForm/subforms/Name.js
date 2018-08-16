import T from 'prop-types';
import React from 'react';
import { InputGroup} from 'reactstrap';
import {AvInput } from 'availity-reactstrap-validation';

const  Name = ({name,onChange}) =>
{
  return (
    <div>
      <InputGroup>
        <AvInput
          name="name_label"
          id="name_label"
          placeholder="Enter VM name..."
          lg
          onChange={onChange}
          value={name}
          required
          />
      </InputGroup>
    </div>
  );
};

export default Name;
